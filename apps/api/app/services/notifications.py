"""Emails about a bill, in two steps so none is sent twice or inside a transaction.

First the notification is set aside (`reserve`) in the same transaction as whatever
caused it. Once that is committed, `deliver` sends the email in a transaction of its own
and writes down how it went.
"""

import logging
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import Engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import set_owner_id
from app.email.content import BillEmail, render_email
from app.email.sender import Attachment, EmailError, EmailMessage, EmailSender
from app.errors import AppError
from app.models import Bill, BillItem, Lease, Notification, Owner, Payment, Tenant, Unit
from app.models.notification import AUTOMATIC_TYPES
from app.pdf.format import format_month
from app.storage import Storage, StorageError

logger = logging.getLogger(__name__)

# Which template each kind of notification uses. A resent bill reads like the first one.
TEMPLATES = {
    "bill": "bill",
    "resend": "bill",
    "reminder_1": "reminder_1",
    "reminder_2": "reminder_2",
    "manual_reminder": "manual_reminder",
    "receipt": "receipt",
}

# How the receipt names each way of paying.
METHOD_LABELS = {
    "transfer": "Transferencia",
    "nequi": "Nequi",
    "cash": "Efectivo",
    "other": "Otro medio",
}


@dataclass(frozen=True)
class ReceiptDetails:
    """The payment a receipt is about."""

    amount: int
    payment_date: date
    method: str


def reserve(session: Session, bill: Bill, kind: str) -> Notification | None:
    """Sets aside a notification for a bill, addressed to its tenant as of now.

    Returns None when it is an automatic one that this bill already has: the unique
    index decides, so the daily task run twice sets it aside only once.
    """
    lease = session.get_one(Lease, bill.lease_id)
    tenant = session.get_one(Tenant, lease.tenant_id)
    notification = Notification(
        owner_id=bill.owner_id, bill_id=bill.id, type=kind, recipient=tenant.email
    )
    try:
        # A savepoint: losing the race must not undo the rest of the transaction.
        with session.begin_nested():
            session.add(notification)
            session.flush()
    except IntegrityError:
        if kind in AUTOMATIC_TYPES:
            return None
        raise
    return notification


def _message(
    session: Session,
    storage: Storage,
    notification: Notification,
    today: date,
    receipt: ReceiptDetails | None,
) -> EmailMessage:
    bill = session.get_one(Bill, notification.bill_id)
    owner = session.get_one(Owner, bill.owner_id)
    lease = session.get_one(Lease, bill.lease_id)
    tenant = session.get_one(Tenant, lease.tenant_id)
    unit = session.get_one(Unit, lease.unit_id)
    item = session.scalars(
        select(BillItem).where(BillItem.bill_id == bill.id).order_by(BillItem.created_at)
    ).first()
    concept = [item.description if item else "Cuenta de cobro"]
    if bill.period:
        concept.append(format_month(bill.period))
    concept.append(unit.name)
    paid = session.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.bill_id == bill.id)
    )

    rendered = render_email(
        TEMPLATES[notification.type],
        BillEmail(
            owner_name=owner.name,
            tenant_name=tenant.name,
            number=bill.number,
            concept=" · ".join(concept),
            total=bill.total,
            balance=bill.total - paid,
            due_date=bill.due_date,
            payment_details=bill.payment_details,
            payment_amount=receipt.amount if receipt else None,
            payment_date=receipt.payment_date if receipt else None,
            payment_method=METHOD_LABELS[receipt.method] if receipt else None,
        ),
        today,
    )
    # A receipt says what was paid; the bill itself the tenant already has.
    attachments = (
        []
        if receipt
        else [
            Attachment(
                f"cuenta-de-cobro-{bill.number:04d}.pdf",
                # The PDF stored when the bill was issued, never a new one.
                storage.download(bill.pdf_path),
                "application/pdf",
            )
        ]
    )
    return EmailMessage(
        to=notification.recipient,
        sender_name=owner.name,
        reply_to=owner.email,
        subject=rendered.subject,
        html=rendered.html,
        text=rendered.text,
        attachments=attachments,
        bcc=owner.email if owner.email_copy else None,
        # One email per notification and day: a second run today cannot repeat it, and
        # tomorrow's retry of a failed one is a new attempt.
        idempotency_key=f"{notification.id}/{today.isoformat()}",
    )


def deliver(
    engine: Engine,
    mailer: EmailSender,
    storage: Storage,
    notification_id: UUID,
    today: date,
    owner_id: UUID | None = None,
    receipt: ReceiptDetails | None = None,
) -> bool:
    """Sends a notification that was set aside and records the outcome.

    Runs after the transaction that set it aside is committed. `owner_id` scopes it for
    the API's role; the daily task's role needs none. Returns whether the email went out.
    """
    with Session(engine) as session, session.begin():
        if owner_id is not None:
            set_owner_id(session, owner_id)
        # Locked, so two deliveries of the same notification cannot both send.
        notification = session.execute(
            select(Notification).where(Notification.id == notification_id).with_for_update()
        ).scalar_one_or_none()
        if notification is None or notification.delivery_status not in ("pending", "failed"):
            return False
        try:
            if notification.type == "receipt" and receipt is None:
                # Its payment is only known to the request that registered it.
                raise EmailError("a receipt cannot be sent again")
            message = _message(session, storage, notification, today, receipt)
            notification.provider_id = mailer.send(message)
        except (EmailError, StorageError):
            logger.exception("could not send notification %s", notification_id)
            notification.delivery_status = "failed"
            return False
        notification.delivery_status = "sent"
        notification.sent_at = func.now()
        return True


# What the owner asks for by hand


def _sendable(bill: Bill) -> None:
    if bill.status == "voided":
        raise AppError(400, "Esta cuenta está anulada y no se puede enviar.", "bill_voided")


def reserve_send(session: Session, bill: Bill) -> Notification:
    """The bill by email: the first time as `bill`, after that as a resend."""
    _sendable(bill)
    return reserve(session, bill, "bill") or reserve(session, bill, "resend")


def reserve_reminder(session: Session, bill: Bill) -> Notification:
    _sendable(bill)
    if bill.status == "paid":
        raise AppError(
            400, "Esta cuenta ya está pagada: no hay nada que recordar.", "bill_has_no_balance"
        )
    return reserve(session, bill, "manual_reminder")
