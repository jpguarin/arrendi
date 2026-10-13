import logging
from io import BytesIO
from uuid import uuid4

from fastapi import BackgroundTasks
from PIL import Image, ImageChops, ImageFilter, ImageOps
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
# A phone saves a JPG with several pictures inside, which Pillow calls MPO.
FORMATS = ("PNG", "JPEG", "MPO")
# How many pixels are worth opening. A photo from a phone has dozens of millions, but a
# JPG can be decoded smaller from the start; a PNG cannot, and every one of its pixels
# takes four bytes of memory.
MAX_PIXELS = {"PNG": 16_000_000, "JPEG": 60_000_000, "MPO": 60_000_000}
# The size it is worked on: plenty for a signature that ends up no larger than `BOX`.
WORKING = (1600, 1600)
BOX = (600, 200)
# The paper is found on a copy this small, where the strokes are thin enough to wipe out.
PAPER = (400, 400)
# How much darker than the paper around it a pixel has to be to count as ink, from 0 to
# 255: below the first it is paper, above the second it is solid ink.
FAINT, SOLID = 25, 70
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
    """Where the browser sends what the owner picked or drew. Nothing stays here."""
    return f"{owner.id}/signature"


def _stored_folder(owner: Owner) -> str:
    """Where the signatures themselves are kept, the owner's and those of their bills.

    Apart from the uploads on purpose: no path in here can be confirmed as a new upload,
    which would read it as a source and delete it.
    """
    return f"{owner.id}/signatures"


def _ink(image: Image.Image) -> Image.Image:
    """How much ink there is at each point of the picture: 0 for paper, 255 for a stroke.

    A drawing has its strokes on nothing at all, but a photo has them on a sheet that is
    never white: it is grey, and darker towards one side. So the paper is worked out
    first, by wiping the strokes off a small copy, and ink is what is darker than it.
    """
    grey = image.convert("L")
    small = grey.copy()
    small.thumbnail(PAPER)
    paper = small.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(4))
    darker = ImageChops.subtract(paper.resize(grey.size, Image.Resampling.BILINEAR), grey)
    span = SOLID - FAINT
    return darker.point(lambda value: max(0, min(255, (value - FAINT) * 255 // span)))


def normalize(raw: bytes) -> bytes:
    """The signature as it is stored: its ink on nothing, cut to it, no larger than `BOX`."""
    try:
        with Image.open(BytesIO(raw)) as opened:
            # Read from the header, before any pixel is decoded.
            if opened.format not in FORMATS:
                raise InvalidImage
            if opened.width * opened.height > MAX_PIXELS[opened.format]:
                raise InvalidImage
            # A JPG can come out of the decoder already smaller, at a fraction of the memory.
            opened.draft("RGB", WORKING)
            # A photo from a phone says which way is up apart from its pixels.
            image = ImageOps.exif_transpose(opened).convert("RGBA")
        image.thumbnail(WORKING, Image.Resampling.LANCZOS)

        # On a white sheet, so what was transparent counts as paper.
        white = Image.new("RGBA", image.size, (255, 255, 255, 255))
        on_paper = Image.alpha_composite(white, image).convert("RGB")
        ink = _ink(on_paper)
        box = ink.point(lambda value: 255 if value > 127 else 0).getbbox()
        if box is None:
            # Nothing but paper.
            raise InvalidImage
        left, top, right, bottom = box
        signature = on_paper.convert("RGBA")
        signature.putalpha(ink)
        signature = signature.crop(
            (
                max(left - MARGIN, 0),
                max(top - MARGIN, 0),
                min(right + MARGIN, signature.width),
                min(bottom + MARGIN, signature.height),
            )
        )
        # Only ever smaller: a small signature is not blown up.
        signature.thumbnail(BOX, Image.Resampling.LANCZOS)
        out = BytesIO()
        signature.save(out, "PNG", optimize=True)
        return out.getvalue()
    except InvalidImage:
        raise
    except Exception as error:
        # Pillow fails in more ways than it documents: OSError, SyntaxError, struct.error…
        # Whatever it is, the file is not an image we can sign with.
        raise InvalidImage from error


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
        path = f"{_stored_folder(owner)}/{uuid4()}/firma.png"
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
