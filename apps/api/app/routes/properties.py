from uuid import UUID

from fastapi import APIRouter

from app.dependencies import CurrentUser, OwnerSession
from app.errors import ErrorResponse
from app.schemas.property import (
    PropertyCreate,
    PropertyResponse,
    PropertyUpdate,
    UnitCreate,
    UnitResponse,
    UnitUpdate,
)
from app.services import properties
from app.services.owners import get_or_create_owner

router = APIRouter(responses={401: {"model": ErrorResponse}})
NOT_FOUND = {404: {"model": ErrorResponse}}


@router.get("/properties")
def list_properties(session: OwnerSession) -> list[PropertyResponse]:
    return properties.list_properties(session)


@router.post("/properties", status_code=201)
def create_property(
    data: PropertyCreate, user: CurrentUser, session: OwnerSession
) -> PropertyResponse:
    # The property points at the owner's row, which the first call of any kind creates.
    owner = get_or_create_owner(session, user)
    return properties.create_property(session, owner.id, data)


@router.patch("/properties/{property_id}", responses=NOT_FOUND)
def update_property(
    property_id: UUID, data: PropertyUpdate, session: OwnerSession
) -> PropertyResponse:
    return properties.update_property(session, property_id, data)


@router.post("/properties/{property_id}/units", status_code=201, responses=NOT_FOUND)
def add_unit(property_id: UUID, data: UnitCreate, session: OwnerSession) -> UnitResponse:
    return properties.add_unit(session, property_id, data)


@router.patch("/units/{unit_id}", responses=NOT_FOUND)
def update_unit(unit_id: UUID, data: UnitUpdate, session: OwnerSession) -> UnitResponse:
    return properties.update_unit(session, unit_id, data)
