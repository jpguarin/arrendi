from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.dependencies import FileStorage, OwnerSession, Today
from app.errors import ErrorResponse
from app.schemas.bill import BillCreate, BillResponse, BillStatusFilter, BillSummary
from app.schemas.document import DocumentUrlResponse
from app.services import bills

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
