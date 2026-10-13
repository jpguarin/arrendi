import logging
from io import BytesIO
from uuid import uuid4

from fastapi import BackgroundTasks
from PIL import Image, ImageChops, ImageOps, UnidentifiedImageError
from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.errors import AppError, not_found, storage_unavailable
from app.models import Bill, Owner
from app.schemas.document import (
    DocumentConfirm,
    DocumentUrlResponse,
    UploadUrlRequest,
    UploadUrlResponse,
)
from app.schemas.settings import SettingsResponse
from app.services import documents
from app.services.owners import settings_response
from app.storage import Storage, StorageError

logger = logging.getLogger(__name__)

# The image the owner signs with. It goes on every bill they issue, so it is kept small:
# whatever they upload is cut down to its strokes and stored as a PNG of this size at most.
TYPES = ("image/png", "image/jpeg")
MAX_SIZE = 2 * 1024 * 1024
MAX_PIXELS = 40_000_000
BOX = (600, 200)
# How far from white a pixel has to be to count as a stroke, from 0 to 255.
INK = 40
MARGIN = 8


class InvalidImage(Exception):
    """The file is not an image that can be read, or it has nothing drawn on it."""


def _unsupported_type() -> AppError:
    return AppError(422, "Solo se aceptan imágenes JPG o PNG.", "unsupported_file_type")


def _too_large() -> AppError:
    return AppError(422, "La imagen supera los 2 MB.", "file_too_large")


def _invalid_image() -> AppError:
    return AppError(
        422,
        "No pudimos leer la firma en esa imagen. Prueba con otra, o dibújala aquí.",
        "invalid_image",
    )


def _folder(owner: Owner) -> str:
    return f"{owner.id}/signature"


def normalize(raw: bytes) -> bytes:
    """The signature as it is stored: a PNG cut down to its strokes, no larger than `BOX`."""
    try:
        with Image.open(BytesIO(raw)) as opened:
            if opened.format not in ("PNG", "JPEG") or opened.width * opened.height > MAX_PIXELS:
                raise InvalidImage
            # A photo from a phone says which way is up apart from its pixels.
            image = ImageOps.exif_transpose(opened).convert("RGBA")
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as error:
        raise InvalidImage from error

    # The strokes are what differs from a white sheet. Around them there is usually a lot
    # of empty paper or canvas, which would leave the signature tiny on the bill.
    white = Image.new("RGBA", image.size, (255, 255, 255, 255))
    on_paper = Image.alpha_composite(white, image).convert("L")
    strokes = ImageChops.invert(on_paper).point(lambda value: 255 if value > INK else 0)
    box = strokes.getbbox()
    if box is None:
        raise InvalidImage
    left, top, right, bottom = box
    image = image.crop(
        (
            max(left - MARGIN, 0),
            max(top - MARGIN, 0),
            min(right + MARGIN, image.width),
            min(bottom + MARGIN, image.height),
        )
    )
    # Only ever smaller: a small signature is not blown up.
    image.thumbnail(BOX, Image.Resampling.LANCZOS)
    out = BytesIO()
    image.save(out, "PNG", optimize=True)
    return out.getvalue()


def create_upload_url(storage: Storage, owner: Owner, data: UploadUrlRequest) -> UploadUrlResponse:
    if data.content_type not in TYPES:
        raise _unsupported_type()
    if data.size > MAX_SIZE:
        raise _too_large()
    return documents.new_upload(storage, _folder(owner), data, "firma")


def _discard(session: Session, storage: Storage, background: BackgroundTasks, path: str) -> None:
    """Deletes a signature the owner no longer uses, unless a bill was issued with it."""
    # A bill keeps the signature it was issued with, and needs the file to be drawn again
    # when it is voided.
    if session.scalar(select(exists().where(Bill.signature_path == path))):
        return
    # After the response, which is after the commit: if saving fails, the owner still
    # points at this file and it must still be there.
    background.add_task(documents.delete_quietly, storage, path)


def confirm_signature(
    session: Session,
    storage: Storage,
    background: BackgroundTasks,
    owner: Owner,
    data: DocumentConfirm,
) -> SettingsResponse:
    folder = _folder(owner)
    # Before touching storage: a path from anywhere else is not ours to read or delete.
    if not documents.is_upload_of(folder, data.path) or data.path.endswith(".pdf"):
        raise not_found()
    if data.path == owner.signature_path:
        return settings_response(owner)
    documents.check_upload(storage, data.path)

    try:
        # Checked again here: what arrived may be larger than what was announced.
        too_large = (storage.size(data.path) or 0) > MAX_SIZE
        raw = None if too_large else storage.download(data.path)
        try:
            signature = None if raw is None else normalize(raw)
        except InvalidImage:
            signature = None
        # What the browser sent is only the source: the signature is stored apart.
        storage.delete(data.path)
        if too_large:
            raise _too_large()
        if signature is None:
            raise _invalid_image()
        path = f"{folder}/{uuid4()}/firma.png"
        storage.upload(path, signature, "image/png")
    except StorageError as error:
        raise storage_unavailable() from error

    previous = owner.signature_path
    owner.signature_path = path
    session.flush()
    if previous:
        _discard(session, storage, background, previous)
    return settings_response(owner)


def get_signature_url(storage: Storage, owner: Owner) -> DocumentUrlResponse:
    if owner.signature_path is None:
        raise AppError(404, "Aún no has subido tu firma.", "signature_not_found")
    return documents.download_url(storage, owner.signature_path)


def remove_signature(
    session: Session, storage: Storage, background: BackgroundTasks, owner: Owner
) -> SettingsResponse:
    """Takes the signature away. The bills already issued keep theirs."""
    previous = owner.signature_path
    owner.signature_path = None
    session.flush()
    if previous:
        _discard(session, storage, background, previous)
    return settings_response(owner)
