from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.auth import AuthUser
from app.errors import AppError
from app.models import Owner
from app.schemas.settings import SettingsResponse, SettingsUpdate


def get_or_create_owner(session: Session, user: AuthUser) -> Owner:
    """Returns the owner of the session, creating their row on the first call.

    The name and email come from the token only when the row is created; after that,
    what the owner saved wins.
    """
    owner = session.get(Owner, user.owner_id)
    if owner is not None:
        return owner

    if not user.email:
        raise AppError(
            400, "Tu cuenta no tiene un correo. Ingresa con otra cuenta.", "email_required"
        )

    # Two first calls can arrive at once (the app opens with several requests).
    session.execute(
        insert(Owner)
        .values(id=user.owner_id, name=user.name or user.email, email=user.email)
        .on_conflict_do_nothing(index_elements=[Owner.id])
    )
    return session.get_one(Owner, user.owner_id)


def settings_response(owner: Owner) -> SettingsResponse:
    return SettingsResponse(
        name=owner.name,
        email=owner.email,
        document_number=owner.document_number,
        payment_details=owner.payment_details,
    )


def update_settings(session: Session, owner: Owner, data: SettingsUpdate) -> SettingsResponse:
    for field, value in data.changes().items():
        setattr(owner, field, value)
    session.flush()
    return settings_response(owner)
