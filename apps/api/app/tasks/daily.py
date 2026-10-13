"""The daily task: issue the month's bills, mark the overdue ones and send reminders.

It runs once a day as `arrendi_tasks`, which sees every owner. Running it twice the same
day changes nothing the second time: the unique indexes of `bills` and `notifications`
decide. And it catches up on its own after a missed day, because every condition is
"already due", never "exactly today".
"""

import logging
import time
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import Engine, exists, func, select, update
from sqlalchemy.orm import Session

from app.email.sender import EmailSender
from app.errors import AppError
from app.models import Bill, Lease, Notification, Owner
from app.models.notification import AUTOMATIC_TYPES
from app.services import bills, notifications
from app.storage import Storage

logger = logging.getLogger(__name__)

REMINDER_1_DAYS = 1
REMINDER_2_DAYS = 7
# A notification set aside this long ago and never sent was cut short; try it again.
STALE_PENDING = timedelta(hours=1)


@dataclass
class DailyResult:
    bills_generated: int = 0
    bills_marked_overdue: int = 0
    emails_sent: int = 0
    errors: int = 0
    # False when time ran out; the next run picks up what is left.
    finished: bool = True


class _Run:
    def __init__(
        self,
        engine: Engine,
        mailer: EmailSender,
        storage: Storage,
        today: date,
        deadline: float | None,
    ) -> None:
        self.engine = engine
        self.mailer = mailer
        self.storage = storage
        self.today = today
        self.deadline = deadline
        self.result = DailyResult()

    def out_of_time(self) -> bool:
        if self.deadline is not None and time.monotonic() >= self.deadline:
            self.result.finished = False
            return True
        return False

    def deliver(self, notification_id: UUID) -> None:
        if notifications.deliver(
            self.engine, self.mailer, self.storage, notification_id, self.today
        ):
            self.result.emails_sent += 1
        else:
            self.result.errors += 1

    # 0. What an earlier run left unsent

    def retry_unsent(self) -> None:
        with Session(self.engine) as session:
            unsent = session.scalars(
                select(Notification.id)
                .join(Bill, Bill.id == Notification.bill_id)
                .where(
                    Notification.type.in_(AUTOMATIC_TYPES),
                    (Notification.delivery_status == "failed")
                    | (
                        (Notification.delivery_status == "pending")
                        & (Notification.created_at < func.now() - STALE_PENDING)
                    ),
                    # A bill that was voided or paid since then needs no email.
                    Bill.status.in_(("pending", "partial", "overdue")),
                )
                .order_by(Notification.created_at)
            ).all()
        for notification_id in unsent:
            if self.out_of_time():
                return
            self.deliver(notification_id)

    # 1. Generate

    def generate_bills(self) -> None:
        period = self.today.replace(day=1)
        with Session(self.engine) as session:
            leases = session.execute(
                select(Lease.id, Lease.auto_send)
                .join(Owner, Owner.id == Lease.owner_id)
                .where(
                    Lease.status == "active",
                    # "Already arrived", so a missed day is made up for on the next one.
                    Owner.send_day <= self.today.day,
                    ~exists().where(
                        Bill.lease_id == Lease.id,
                        Bill.origin == "monthly",
                        Bill.period == period,
                        Bill.status != "voided",
                    ),
                )
                .order_by(Lease.owner_id, Lease.created_at, Lease.id)
            ).all()
        for lease_id, auto_send in leases:
            if self.out_of_time():
                return
            self.generate_bill(lease_id, auto_send)

    def generate_bill(self, lease_id: UUID, auto_send: bool) -> None:
        notification_id = None
        try:
            # One transaction per lease: a failure here rolls back only this bill.
            with Session(self.engine) as session, session.begin():
                bill = bills.issue_monthly_bill(session, self.storage, self.today, lease_id)
                # A bill that charges a late fee waits for the owner: a payment that came
                # in time but is not entered yet would make the fee a mistake, and a bill
                # already sent is hard to take back.
                if auto_send and not bills.charges_late_fee(session, bill.id):
                    notification = notifications.reserve(session, bill, "bill")
                    notification_id = notification.id if notification else None
        except AppError as error:
            if error.code in ("bill_already_exists", "lease_not_active"):
                # Someone got there first, or the lease ended meanwhile. Nothing to do.
                return
            logger.exception("could not issue the bill of lease %s", lease_id)
            self.result.errors += 1
            return
        except Exception:
            logger.exception("could not issue the bill of lease %s", lease_id)
            self.result.errors += 1
            return
        self.result.bills_generated += 1
        # After the commit, never inside the transaction.
        if notification_id is not None:
            self.deliver(notification_id)

    # 2. Mark overdue

    def mark_overdue(self) -> None:
        with Session(self.engine) as session, session.begin():
            marked = session.execute(
                update(Bill)
                .where(Bill.status.in_(("pending", "partial")), Bill.due_date < self.today)
                .values(status="overdue")
            )
            self.result.bills_marked_overdue = marked.rowcount

    # 3. Remind

    def send_reminders(self) -> None:
        reminded: set[UUID] = set()
        for kind, days, enabled in (
            ("reminder_1", REMINDER_1_DAYS, Owner.reminder_1),
            ("reminder_2", REMINDER_2_DAYS, Owner.reminder_2),
        ):
            with Session(self.engine) as session:
                due = session.scalars(
                    select(Bill.id)
                    .join(Owner, Owner.id == Bill.owner_id)
                    .where(
                        Bill.status == "overdue",
                        Bill.due_date <= self.today - timedelta(days=days),
                        enabled,
                        # Only bills the tenant actually received.
                        exists().where(
                            Notification.bill_id == Bill.id,
                            Notification.type.in_(("bill", "resend")),
                            Notification.delivery_status == "sent",
                        ),
                        ~exists().where(Notification.bill_id == Bill.id, Notification.type == kind),
                    )
                    .order_by(Bill.owner_id, Bill.number)
                ).all()
            for bill_id in due:
                # At most one reminder per bill in each run.
                if bill_id in reminded:
                    continue
                if self.out_of_time():
                    return
                reminded.add(bill_id)
                self.remind(bill_id, kind)

    def remind(self, bill_id: UUID, kind: str) -> None:
        try:
            with Session(self.engine) as session, session.begin():
                notification = notifications.reserve(session, session.get_one(Bill, bill_id), kind)
                notification_id = notification.id if notification else None
        except Exception:
            logger.exception("could not set aside the %s of bill %s", kind, bill_id)
            self.result.errors += 1
            return
        if notification_id is not None:
            self.deliver(notification_id)


def run_daily(
    engine: Engine,
    mailer: EmailSender,
    storage: Storage,
    today: date,
    deadline: float | None = None,
) -> DailyResult:
    """Runs the three steps. `deadline` is a `time.monotonic()` value to stop by."""
    run = _Run(engine, mailer, storage, today, deadline)
    run.retry_unsent()
    run.generate_bills()
    run.mark_overdue()
    run.send_reminders()
    logger.info("daily task for %s: %s", today, asdict(run.result))
    return run.result
