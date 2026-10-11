from uuid import UUID

from fastapi import APIRouter

from app.dependencies import OwnerSession
from app.errors import ErrorResponse
from app.schemas.lease import LeaseCreate, LeaseResponse, LeaseUpdate
from app.services import leases

router = APIRouter(responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})


@router.post("/leases", status_code=201, responses={409: {"model": ErrorResponse}})
def create_lease(data: LeaseCreate, session: OwnerSession) -> LeaseResponse:
    return leases.create_lease(session, data)


@router.get("/leases/{lease_id}")
def get_lease(lease_id: UUID, session: OwnerSession) -> LeaseResponse:
    return leases.lease_response(session, leases.get_lease(session, lease_id))


@router.patch("/leases/{lease_id}")
def update_lease(lease_id: UUID, data: LeaseUpdate, session: OwnerSession) -> LeaseResponse:
    return leases.update_lease(session, lease_id, data)


@router.post("/leases/{lease_id}/end", responses={400: {"model": ErrorResponse}})
def end_lease(lease_id: UUID, session: OwnerSession) -> LeaseResponse:
    return leases.end_lease(session, lease_id)
