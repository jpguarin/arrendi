from fastapi import APIRouter

from app.dependencies import CurrentUser, OwnerSession
from app.errors import ErrorResponse
from app.schemas.settings import SettingsResponse, SettingsUpdate
from app.services import owners

router = APIRouter(responses={401: {"model": ErrorResponse}})

# What the owner sets up once: who they are and how they get paid. Both go on every bill.


@router.get("/settings")
def get_settings(user: CurrentUser, session: OwnerSession) -> SettingsResponse:
    return owners.settings_response(owners.get_or_create_owner(session, user))


@router.patch("/settings")
def update_settings(
    data: SettingsUpdate, user: CurrentUser, session: OwnerSession
) -> SettingsResponse:
    return owners.update_settings(session, owners.get_or_create_owner(session, user), data)
