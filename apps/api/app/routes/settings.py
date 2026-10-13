from fastapi import APIRouter, BackgroundTasks

from app.dependencies import CurrentUser, FileStorage, OwnerSession
from app.errors import ErrorResponse
from app.schemas.document import (
    DocumentConfirm,
    DocumentUrlResponse,
    UploadUrlRequest,
    UploadUrlResponse,
)
from app.schemas.settings import SettingsResponse, SettingsUpdate
from app.services import owners, signature

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


# The signature that goes at the foot of every bill. The file never goes through the API:
# the browser sends it to storage with a signed link, like the signed lease.

NOT_FOUND = {404: {"model": ErrorResponse}}


@router.post("/settings/signature/upload-url")
def create_signature_upload_url(
    data: UploadUrlRequest, user: CurrentUser, session: OwnerSession, storage: FileStorage
) -> UploadUrlResponse:
    owner = owners.get_or_create_owner(session, user)
    return signature.create_upload_url(storage, owner, data)


@router.post("/settings/signature", responses=NOT_FOUND | {400: {"model": ErrorResponse}})
def confirm_signature(
    data: DocumentConfirm,
    user: CurrentUser,
    session: OwnerSession,
    storage: FileStorage,
    background: BackgroundTasks,
) -> SettingsResponse:
    owner = owners.get_or_create_owner(session, user)
    return signature.confirm_signature(session, storage, background, owner, data)


@router.get("/settings/signature", responses=NOT_FOUND)
def get_signature_url(
    user: CurrentUser, session: OwnerSession, storage: FileStorage
) -> DocumentUrlResponse:
    return signature.get_signature_url(storage, owners.get_or_create_owner(session, user))


@router.delete("/settings/signature")
def remove_signature(
    user: CurrentUser, session: OwnerSession, storage: FileStorage, background: BackgroundTasks
) -> SettingsResponse:
    owner = owners.get_or_create_owner(session, user)
    return signature.remove_signature(session, storage, background, owner)
