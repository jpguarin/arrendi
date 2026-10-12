from datetime import date

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import Bill, Lease, Notification, Tenant, Unit
from app.schemas.summary import BouncedEmail, SummaryResponse
from app.services.bills import BILL_MONTH, bill_summaries

# Every query here runs inside the owner's transaction: row security already limits it to
# their rows.

RECEIVABLE = ("pending", "partial", "overdue")


def get_summary(session: Session, month: date) -> SummaryResponse:
    """The home screen: how the month is going and who owes what. `month` is its first day."""
    of_the_month = bill_summaries(
        session,
        select(Bill)
        .where(BILL_MONTH == month, Bill.status != "voided")
        .order_by(Bill.number.desc()),
    )
    expected = sum(bill.total for bill in of_the_month)
    # A payment counts in the month of its bill, not in the month it was received, so
    # these figures are the same ones the list of bills shows for the month.
    collected = sum(bill.total - bill.balance for bill in of_the_month)

    receivable = bill_summaries(
        session,
        select(Bill)
        .where(Bill.status.in_(RECEIVABLE))
        .order_by(case((Bill.status == "overdue", 0), else_=1), Bill.due_date, Bill.number),
    )
    earlier = session.scalars(
        select(Bill.id).where(Bill.status.in_(RECEIVABLE), BILL_MONTH < month)
    ).all()

    units_total = session.scalar(select(func.count()).select_from(Unit))
    units_overdue = session.scalar(
        select(func.count(func.distinct(Lease.unit_id)))
        .join(Bill, Bill.lease_id == Lease.id)
        .where(Lease.status == "active", Bill.status == "overdue")
    )

    bounced = session.execute(
        select(Bill.id, Bill.number, Unit.name, Tenant.name, Notification.recipient)
        .join(Bill, Bill.id == Notification.bill_id)
        .join(Lease, Lease.id == Bill.lease_id)
        .join(Unit, Unit.id == Lease.unit_id)
        .join(Tenant, Tenant.id == Lease.tenant_id)
        # Only where it still matters: a bill someone has yet to pay.
        .where(Notification.delivery_status == "bounced", Bill.status.in_(RECEIVABLE))
        .order_by(Bill.number.desc(), Notification.created_at.desc())
    ).all()
    # One line per bill, however many of its emails bounced.
    bounced = list({row[0]: row for row in bounced}.values())

    return SummaryResponse(
        month=month,
        expected=expected,
        collected=collected,
        pending=expected - collected,
        previous_pending=sum(bill.balance for bill in receivable if bill.id in set(earlier)),
        units_total=units_total,
        units_overdue=units_overdue,
        receivable=receivable,
        paid=[bill for bill in of_the_month if bill.status == "paid"],
        bounced=[
            BouncedEmail(
                bill_id=bill_id,
                number=number,
                unit_name=unit_name,
                tenant_name=tenant_name,
                recipient=recipient,
            )
            for bill_id, number, unit_name, tenant_name, recipient in bounced
        ],
    )
