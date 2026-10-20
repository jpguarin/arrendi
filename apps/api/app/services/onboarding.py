from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import AuthUser
from app.errors import conflict
from app.models import Owner, Property, Unit
from app.schemas.onboarding import OnboardingRequest, OnboardingResponse
from app.services.leases import create_lease_for_unit, lease_response
from app.services.owners import get_or_create_owner, missing_profile
from app.services.properties import has_properties, property_response


def complete_onboarding(
    session: Session, user: AuthUser, data: OnboardingRequest
) -> OnboardingResponse:
    """Creates the first property, its units and, if sent, the first lease.

    Only once the owner's data (document, payment details and signature) is filled in.

    It all happens in the request's transaction: if any part fails, nothing is created.
    """
    owner = get_or_create_owner(session, user)
    # Locks the owner's row, so a double tap waits here and then finds the property.
    session.execute(select(Owner.id).where(Owner.id == owner.id).with_for_update())
    if has_properties(session):
        raise conflict(
            "Ya creaste tu primer inmueble. Agrega los demás desde Inmuebles.",
            "onboarding_already_complete",
        )

    # The owner's data goes on every bill: a new owner fills it in first.
    missing = missing_profile(owner)
    if missing:
        listed = missing[0] if len(missing) == 1 else f"{', '.join(missing[:-1])} y {missing[-1]}"
        raise conflict(
            f"Antes de crear tu primer inmueble, completa tus datos: {listed}.",
            "profile_incomplete",
        )

    new_property = Property(owner_id=owner.id, **data.property.model_dump())
    session.add(new_property)
    session.flush()

    # Units are listed by creation time, and `now()` is the same for the whole transaction.
    # The clock time, one insert at a time, keeps the order the owner gave them.
    units = []
    for unit in data.units:
        new_unit = Unit(
            owner_id=owner.id,
            property_id=new_property.id,
            created_at=func.clock_timestamp(),
            updated_at=func.clock_timestamp(),
            **unit.model_dump(),
        )
        session.add(new_unit)
        session.flush()
        units.append(new_unit)

    lease = None
    if data.lease is not None:
        lease = create_lease_for_unit(
            session, units[data.lease.unit_index], data.lease, tenant=data.lease.tenant
        )

    return OnboardingResponse(
        property=property_response(session, new_property),
        lease=lease_response(session, lease) if lease else None,
    )
