from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import Engine

from app.dependencies import FileStorage, Mailer, OwnerSession, Today, get_db_engine
from app.errors import ErrorResponse
from app.schemas.bill import BillResponse
from app.schemas.document import (
    DocumentConfirm,
    DocumentUrlResponse,
    UploadUrlRequest,
    UploadUrlResponse,
)
from app.schemas.payment import PaymentCreate
from app.services import bills, notifications, payments

router = APIRouter(responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
BAD_REQUEST = {400: {"model": ErrorResponse}}

# Every change answers with the whole bill: its status and balance are what changed.


@router.post("/bills/{bill_id}/payments", status_code=201, responses=BAD_REQUEST)
def register_payment(
    bill_id: UUID,
    data: PaymentCreate,
    session: OwnerSession,
    engine: Annotated[Engine, Depends(get_db_engine)],
    mailer: Mailer,
    storage: FileStorage,
    today: Today,
    background: BackgroundTasks,
) -> BillResponse:
    bill, payment = payments.register_payment(session, today, bill_id, data)
    if data.send_receipt:
        # Set aside here; the email goes out after the response, which is after the commit.
        receipt = notifications.reserve(session, bill, "receipt")
        background.add_task(
            notifications.deliver,
            engine,
            mailer,
            storage,
            receipt.id,
            today,
            bill.owner_id,
            notifications.ReceiptDetails(payment.amount, payment.payment_date, payment.method),
        )
    return bills.bill_response(session, bill)


@router.delete("/payments/{payment_id}")
def delete_payment(
    payment_id: UUID,
    session: OwnerSession,
    storage: FileStorage,
    today: Today,
    background: BackgroundTasks,
) -> BillResponse:
    bill = payments.delete_payment(session, storage, background, today, payment_id)
    return bills.bill_response(session, bill)


# The proof of payment. The file never goes through the API: the browser sends it to
# storage with a signed link, like the signed lease.


@router.post("/payments/{payment_id}/proof/upload-url")
def create_proof_upload_url(
    payment_id: UUID, data: UploadUrlRequest, session: OwnerSession, storage: FileStorage
) -> UploadUrlResponse:
    return payments.create_proof_upload_url(session, storage, payment_id, data)


@router.post("/payments/{payment_id}/proof", responses=BAD_REQUEST)
def confirm_proof(
    payment_id: UUID,
    data: DocumentConfirm,
    session: OwnerSession,
    storage: FileStorage,
    background: BackgroundTasks,
) -> BillResponse:
    payment = payments.confirm_proof(session, storage, background, payment_id, data)
    return bills.bill_response(session, bills.get_bill(session, payment.bill_id))


@router.get("/payments/{payment_id}/proof")
def get_proof_url(
    payment_id: UUID, session: OwnerSession, storage: FileStorage
) -> DocumentUrlResponse:
    return payments.get_proof_url(session, storage, payment_id)
