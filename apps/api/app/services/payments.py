from datetime import date
from uuid import UUID

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import AppError, not_found
from app.models import Bill, Payment
from app.pdf.format import format_pesos
from app.schemas.document import (
    DocumentConfirm,
    DocumentUrlResponse,
    UploadUrlRequest,
    UploadUrlResponse,
)
from app.schemas.payment import PaymentCreate
from app.services import documents
from app.services.bills import paid_amount
from app.storage import Storage

# Every query here runs inside the owner's transaction: row security already limits it to
# their rows, so another owner's id simply finds nothing.


def _locked_bill(session: Session, bill_id: UUID) -> Bill:
    """The bill, locked until the transaction ends.

    Whoever registers or removes a payment on it next waits here and sees this one's
    result, so two payments at once can never add up to more than the balance.
    """
    bill = session.execute(
        select(Bill)
        .where(Bill.id == bill_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalar_one_or_none()
    if bill is None:
        raise not_found()
    return bill


def recalculate_status(session: Session, bill: Bill, today: date) -> None:
    """Sets the status the bill's payments and due date call for. A voided one stays."""
    if bill.status == "voided":
        return
    paid = paid_amount(session, bill.id)
    if paid >= bill.total:
        bill.status = "paid"
    elif bill.due_date < today:
        # A partial payment on an overdue bill leaves it overdue until the balance is paid.
        bill.status = "overdue"
    elif paid > 0:
        bill.status = "partial"
    else:
        bill.status = "pending"
    session.flush()


def register_payment(
    session: Session, today: date, bill_id: UUID, data: PaymentCreate
) -> tuple[Bill, Payment]:
    bill = _locked_bill(session, bill_id)
    if bill.status == "voided":
        raise AppError(400, "Esta cuenta está anulada y no admite pagos.", "bill_voided")
    if bill.status == "paid":
        raise AppError(400, "Esta cuenta ya está pagada.", "bill_already_paid")
    if data.payment_date > today:
        raise AppError(
            400, "La fecha del pago no puede ser posterior a hoy.", "payment_date_in_future"
        )
    balance = bill.total - paid_amount(session, bill.id)
    # Provisional: a payment above the balance is refused rather than kept as credit.
    if data.amount > balance:
        raise AppError(
            400,
            f"El pago supera el saldo de la cuenta, que es {format_pesos(balance)}.",
            "payment_exceeds_balance",
        )

    payment = Payment(
        owner_id=bill.owner_id,
        bill_id=bill.id,
        payment_date=data.payment_date,
        amount=data.amount,
        method=data.method,
    )
    session.add(payment)
    session.flush()
    recalculate_status(session, bill, today)
    return bill, payment


def get_payment(session: Session, payment_id: UUID) -> Payment:
    payment = session.get(Payment, payment_id)
    if payment is None:
        raise not_found()
    return payment


def delete_payment(
    session: Session,
    storage: Storage,
    background: BackgroundTasks,
    today: date,
    payment_id: UUID,
) -> Bill:
    """Removes a payment entered by mistake, and its proof. The bill goes back to the
    status it calls for, also if it was paid."""
    payment = get_payment(session, payment_id)
    bill = _locked_bill(session, payment.bill_id)
    proof = payment.proof_path
    session.delete(payment)
    session.flush()
    recalculate_status(session, bill, today)
    if proof:
        # After the response, which is after the commit: if deleting fails, the payment
        # is still there and so must be its proof.
        background.add_task(documents.delete_quietly, storage, proof)
    return bill


# The proof of payment. Same three steps as the signed lease.


def _folder(payment: Payment) -> str:
    return f"{payment.owner_id}/proofs/{payment.id}"


def create_proof_upload_url(
    session: Session, storage: Storage, payment_id: UUID, data: UploadUrlRequest
) -> UploadUrlResponse:
    payment = get_payment(session, payment_id)
    return documents.new_upload(storage, _folder(payment), data, "comprobante")


def confirm_proof(
    session: Session,
    storage: Storage,
    background: BackgroundTasks,
    payment_id: UUID,
    data: DocumentConfirm,
) -> Payment:
    payment = get_payment(session, payment_id)
    # Before touching storage: a path from anywhere else is not ours to read or delete.
    if not documents.is_upload_of(_folder(payment), data.path):
        raise not_found()
    if data.path == payment.proof_path:
        return payment
    documents.check_upload(storage, data.path)

    previous = payment.proof_path
    payment.proof_path = data.path
    session.flush()
    if previous:
        background.add_task(documents.delete_quietly, storage, previous)
    return payment


def get_proof_url(session: Session, storage: Storage, payment_id: UUID) -> DocumentUrlResponse:
    payment = get_payment(session, payment_id)
    if payment.proof_path is None:
        raise AppError(404, "Este pago no tiene comprobante.", "document_not_found")
    return documents.download_url(storage, payment.proof_path)
