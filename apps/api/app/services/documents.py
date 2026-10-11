import re
import unicodedata
from uuid import UUID, uuid4

from fastapi import BackgroundTasks
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.errors import AppError, not_found
from app.models import Lease
from app.schemas.document import (
    DocumentConfirm,
    DocumentUrlResponse,
    UploadUrlRequest,
    UploadUrlResponse,
)
from app.schemas.lease import LeaseResponse
from app.services.leases import get_lease, lease_response
from app.storage import Storage, StorageError

# Provisional limit; see docs/decisiones.md.
MAX_SIZE = 10 * 1024 * 1024
DOWNLOAD_LINK_SECONDS = 300

EXTENSIONS = {"application/pdf": "pdf", "image/jpeg": "jpg", "image/png": "png"}
# How each kind of file starts. The declared type and the extension can lie.
SIGNATURES = {"pdf": b"%PDF-", "jpg": b"\xff\xd8\xff", "png": b"\x89PNG\r\n\x1a\n"}
SIGNATURE_LENGTH = max(len(signature) for signature in SIGNATURES.values())
MAX_NAME_LENGTH = 80


def _unsupported_type() -> AppError:
    return AppError(422, "Solo se aceptan archivos PDF, JPG o PNG.", "unsupported_file_type")


def _too_large() -> AppError:
    return AppError(422, "El archivo supera los 10 MB.", "file_too_large")


def storage_unavailable() -> AppError:
    return AppError(
        503,
        "No pudimos acceder a tus archivos. Inténtalo de nuevo en un momento.",
        "storage_unavailable",
    )


def safe_name(filename: str, extension: str) -> str:
    """A name storage accepts: plain letters, digits, dots and dashes, with our extension."""
    name = filename.replace("\\", "/").rsplit("/", 1)[-1]
    stem = name.rsplit(".", 1)[0] if "." in name else name
    plain = unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode()
    plain = re.sub(r"[^A-Za-z0-9_-]+", "-", plain).strip("-_")[:MAX_NAME_LENGTH]
    return f"{plain or 'contrato'}.{extension}"


def _folder(lease: Lease) -> str:
    return f"{lease.owner_id}/leases/{lease.id}"


def create_upload_url(
    session: Session, storage: Storage, lease_id: UUID, data: UploadUrlRequest
) -> UploadUrlResponse:
    lease = get_lease(session, lease_id)
    extension = EXTENSIONS.get(data.content_type)
    if extension is None:
        raise _unsupported_type()
    if data.size > MAX_SIZE:
        raise _too_large()

    # A new folder per upload: the file being replaced stays untouched until this one is
    # confirmed, and a link can never overwrite a file that is already attached.
    path = f"{_folder(lease)}/{uuid4()}/{safe_name(data.filename, extension)}"
    try:
        return UploadUrlResponse(upload_url=storage.create_upload_url(path), path=path)
    except StorageError as error:
        raise storage_unavailable() from error


def _is_upload_of(lease: Lease, path: str) -> bool:
    """Whether the path is one `create_upload_url` could have handed out for this lease."""
    pattern = rf"{re.escape(_folder(lease))}/[0-9a-f-]{{36}}/[A-Za-z0-9_-]+\.(pdf|jpg|png)"
    return re.fullmatch(pattern, path) is not None


def _delete_quietly(storage: Storage, path: str) -> None:
    try:
        storage.delete(path)
    except StorageError:
        # The file stays behind, attached to nothing. Not worth failing the request.
        pass


def confirm_document(
    session: Session,
    storage: Storage,
    background: BackgroundTasks,
    lease_id: UUID,
    data: DocumentConfirm,
) -> LeaseResponse:
    lease = get_lease(session, lease_id)
    # Before touching storage: a path from anywhere else is not ours to read or delete.
    if not _is_upload_of(lease, data.path):
        raise not_found()
    if data.path == lease.document_path:
        return lease_response(session, lease)

    try:
        size = storage.size(data.path)
        if size is None:
            raise AppError(
                400, "No recibimos el archivo. Súbelo de nuevo.", "document_not_uploaded"
            )
        problem = None
        if size > MAX_SIZE:
            problem = _too_large()
        else:
            extension = data.path.rsplit(".", 1)[-1]
            start = storage.read_start(data.path, SIGNATURE_LENGTH)
            if not start.startswith(SIGNATURES[extension]):
                problem = _unsupported_type()
        if problem is not None:
            storage.delete(data.path)
            raise problem
    except StorageError as error:
        raise storage_unavailable() from error

    previous = lease.document_path
    lease.document_path = data.path
    lease.document_uploaded_at = func.now()
    session.flush()
    session.refresh(lease)
    if previous:
        # After the response, which is after the commit: if saving fails, the lease still
        # points at the previous file and it must still be there.
        background.add_task(_delete_quietly, storage, previous)
    return lease_response(session, lease)


def get_document_url(session: Session, storage: Storage, lease_id: UUID) -> DocumentUrlResponse:
    lease = get_lease(session, lease_id)
    if lease.document_path is None:
        raise AppError(404, "Este contrato no tiene documento.", "document_not_found")
    try:
        url = storage.create_download_url(lease.document_path, DOWNLOAD_LINK_SECONDS)
    except StorageError as error:
        raise storage_unavailable() from error
    return DocumentUrlResponse(
        url=url,
        name=lease.document_path.rsplit("/", 1)[-1],
        expires_in=DOWNLOAD_LINK_SECONDS,
    )
