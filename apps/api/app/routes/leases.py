from uuid import UUID

from fastapi import APIRouter, BackgroundTasks

from app.dependencies import FileStorage, OwnerSession
from app.errors import ErrorResponse
from app.schemas.document import (
    DocumentConfirm,
    DocumentUrlResponse,
    UploadUrlRequest,
    UploadUrlResponse,
)
from app.schemas.lease import LeaseCreate, LeaseResponse, LeaseUpdate
from app.services import documents, leases

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


# The signed lease. The file never goes through the API (a request to a Vercel function
# cannot carry more than 4.5 MB): the browser sends it to storage with a signed link.


@router.post("/leases/{lease_id}/document/upload-url")
def create_document_upload_url(
    lease_id: UUID, data: UploadUrlRequest, session: OwnerSession, storage: FileStorage
) -> UploadUrlResponse:
    return documents.create_upload_url(session, storage, lease_id, data)


@router.post("/leases/{lease_id}/document", responses={400: {"model": ErrorResponse}})
def confirm_document(
    lease_id: UUID,
    data: DocumentConfirm,
    session: OwnerSession,
    storage: FileStorage,
    background: BackgroundTasks,
) -> LeaseResponse:
    return documents.confirm_document(session, storage, background, lease_id, data)


@router.get("/leases/{lease_id}/document")
def get_document_url(
    lease_id: UUID, session: OwnerSession, storage: FileStorage
) -> DocumentUrlResponse:
    return documents.get_document_url(session, storage, lease_id)
