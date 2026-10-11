from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy import Engine

from app.dependencies import FileStorage, Mailer, OwnerSession, Today, get_db_engine
from app.errors import ErrorResponse
from app.schemas.bill import BillCreate, BillResponse, BillStatusFilter, BillSummary
from app.schemas.document import DocumentUrlResponse
from app.services import bills, notifications

router = APIRouter(responses={401: {"model": ErrorResponse}})
NOT_FOUND = {404: {"model": ErrorResponse}}
# What issuing a bill can answer besides 201.
ISSUE = NOT_FOUND | {
    400: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    503: {"model": ErrorResponse},
}


@router.post("/leases/{lease_id}/bills", status_code=201, responses=ISSUE)
def issue_monthly_bill(
    lease_id: UUID, session: OwnerSession, storage: FileStorage, today: Today
) -> BillResponse:
    """The bill of the current month, by hand. The daily task issues the same one."""
    bill = bills.issue_monthly_bill(session, storage, today, lease_id)
    return bills.bill_response(session, bill)


@router.post("/bills", status_code=201, responses=ISSUE)
def create_bill(
    data: BillCreate, session: OwnerSession, storage: FileStorage, today: Today
) -> BillResponse:
    bill = bills.issue_manual_bill(session, storage, today, data)
    return bills.bill_response(session, bill)


@router.get("/bills")
def list_bills(
    session: OwnerSession,
    unit_id: UUID | None = None,
    status: BillStatusFilter | None = None,
    from_date: Annotated[date | None, Query(alias="from")] = None,
    to_date: Annotated[date | None, Query(alias="to")] = None,
) -> list[BillSummary]:
    return bills.list_bills(session, unit_id, status, from_date, to_date)


@router.get("/bills/{bill_id}", responses=NOT_FOUND)
def get_bill(bill_id: UUID, session: OwnerSession) -> BillResponse:
    return bills.bill_response(session, bills.get_bill(session, bill_id))


@router.get("/bills/{bill_id}/pdf", responses=NOT_FOUND | {503: {"model": ErrorResponse}})
def get_pdf_url(bill_id: UUID, session: OwnerSession, storage: FileStorage) -> DocumentUrlResponse:
    return bills.get_pdf_url(session, storage, bill_id)


@router.post("/bills/{bill_id}/void", responses=NOT_FOUND | {400: {"model": ErrorResponse}})
def void_bill(
    bill_id: UUID, session: OwnerSession, storage: FileStorage, background: BackgroundTasks
) -> BillResponse:
    return bills.void_bill(session, storage, background, bill_id)


# Email. The notification is set aside here and the email goes out after the response,
# which is after the commit: never inside the transaction.

DbEngine = Annotated[Engine, Depends(get_db_engine)]
EMAIL = NOT_FOUND | {400: {"model": ErrorResponse}}


@router.post("/bills/{bill_id}/send", responses=EMAIL)
def send_bill(
    bill_id: UUID,
    session: OwnerSession,
    engine: DbEngine,
    mailer: Mailer,
    storage: FileStorage,
    today: Today,
    background: BackgroundTasks,
) -> BillResponse:
    """Sends the bill to the tenant, or sends it again."""
    bill = bills.get_bill(session, bill_id)
    notification = notifications.reserve_send(session, bill)
    background.add_task(
        notifications.deliver, engine, mailer, storage, notification.id, today, bill.owner_id
    )
    return bills.bill_response(session, bill)


@router.post("/bills/{bill_id}/remind", responses=EMAIL)
def remind_bill(
    bill_id: UUID,
    session: OwnerSession,
    engine: DbEngine,
    mailer: Mailer,
    storage: FileStorage,
    today: Today,
    background: BackgroundTasks,
) -> BillResponse:
    """Reminds the tenant of a bill that still has a balance."""
    bill = bills.get_bill(session, bill_id)
    notification = notifications.reserve_reminder(session, bill)
    background.add_task(
        notifications.deliver, engine, mailer, storage, notification.id, today, bill.owner_id
    )
    return bills.bill_response(session, bill)
