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


# What every bill needs from its owner and has no default, in the order the owner reads it.
PROFILE = (
    ("document_number", "número de documento"),
    ("payment_details", "datos de pago"),
    ("signature_path", "firma"),
)


def missing_profile(owner: Owner) -> list[str]:
    """What the owner still has to fill in before their first property, by name."""
    return [name for column, name in PROFILE if not getattr(owner, column)]


def settings_response(owner: Owner) -> SettingsResponse:
    return SettingsResponse(
        name=owner.name,
        email=owner.email,
        document_type=owner.document_type,
        document_number=owner.document_number,
        payment_details=owner.payment_details,
        has_signature=owner.signature_path is not None,
        send_day=owner.send_day,
        reminder_1=owner.reminder_1,
        reminder_2=owner.reminder_2,
        email_copy=owner.email_copy,
    )


def update_settings(session: Session, owner: Owner, data: SettingsUpdate) -> SettingsResponse:
    for field, value in data.changes().items():
        setattr(owner, field, value)
    session.flush()
    return settings_response(owner)
