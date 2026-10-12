from datetime import date
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import AppError, conflict, not_found
from app.models import Lease, Property, Tenant, Unit
from app.schemas.lease import (
    LeaseCreate,
    LeaseResponse,
    LeaseTerms,
    LeaseUnit,
    LeaseUpdate,
    TenantCreate,
    TenantResponse,
)
from app.services.bills import recent_bills

# Every query here runs inside the owner's transaction: row security already limits it to
# their rows, so another owner's id simply finds nothing.

ONE_ACTIVE_PER_UNIT = "leases_one_active_per_unit"


def _unit_has_active_lease() -> AppError:
    return conflict(
        "Esta unidad ya tiene un contrato activo. Termínalo antes de crear otro.",
        "unit_has_active_lease",
    )


def _check_dates(start_date: date, end_date: date | None) -> None:
    if end_date is not None and end_date <= start_date:
        raise AppError(
            422, "La fecha de fin debe ser posterior a la de inicio.", "invalid_lease_dates"
        )


def lease_response(session: Session, lease: Lease) -> LeaseResponse:
    unit = session.get_one(Unit, lease.unit_id)
    parent = session.get_one(Property, unit.property_id)
    tenant = session.get_one(Tenant, lease.tenant_id)
    return LeaseResponse(
        id=lease.id,
        status=lease.status,
        rent=lease.rent,
        due_day=lease.due_day,
        start_date=lease.start_date,
        end_date=lease.end_date,
        deposit=lease.deposit,
        charge_deposit=lease.charge_deposit,
        auto_send=lease.auto_send,
        payment_details=lease.payment_details,
        document_name=lease.document_path.rsplit("/", 1)[-1] if lease.document_path else None,
        document_uploaded_at=lease.document_uploaded_at,
        unit=LeaseUnit(
            id=unit.id,
            name=unit.name,
            use=unit.use,
            property_id=parent.id,
            property_name=parent.name,
        ),
        tenant=TenantResponse(
            id=tenant.id,
            name=tenant.name,
            email=tenant.email,
            document_type=tenant.document_type,
            document_number=tenant.document_number,
            phone=tenant.phone,
        ),
        recent_bills=recent_bills(session, lease.id),
    )


def get_lease(session: Session, lease_id: UUID) -> Lease:
    lease = session.get(Lease, lease_id)
    if lease is None:
        raise not_found()
    return lease


def create_lease_for_unit(
    session: Session,
    unit: Unit,
    terms: LeaseTerms,
    tenant: TenantCreate | None = None,
    tenant_id: UUID | None = None,
) -> Lease:
    """Creates the lease of a unit the caller already found, and its tenant if it is new."""
    _check_dates(terms.start_date, terms.end_date)

    if tenant is not None:
        new_tenant = Tenant(owner_id=unit.owner_id, **tenant.model_dump())
        session.add(new_tenant)
        session.flush()
        tenant_id = new_tenant.id
    elif session.get(Tenant, tenant_id) is None:
        raise not_found()

    lease = Lease(
        owner_id=unit.owner_id,
        unit_id=unit.id,
        tenant_id=tenant_id,
        **terms.model_dump(include=set(LeaseTerms.model_fields)),
    )
    session.add(lease)
    try:
        session.flush()
    except IntegrityError as error:
        # The unique index decides, so two requests at once cannot both win. The error
        # rolls back the whole request, including the tenant created above.
        if getattr(error.orig.diag, "constraint_name", None) == ONE_ACTIVE_PER_UNIT:
            raise _unit_has_active_lease() from error
        raise
    return lease


def create_lease(session: Session, data: LeaseCreate) -> LeaseResponse:
    # First, so another owner's unit is a 404 whether or not it is rented.
    unit = session.get(Unit, data.unit_id)
    if unit is None:
        raise not_found()
    lease = create_lease_for_unit(session, unit, data, data.tenant, data.tenant_id)
    return lease_response(session, lease)


def update_lease(session: Session, lease_id: UUID, data: LeaseUpdate) -> LeaseResponse:
    lease = get_lease(session, lease_id)
    changes = data.changes()
    tenant_changes = changes.pop("tenant", None)

    for field, value in changes.items():
        setattr(lease, field, value)
    _check_dates(lease.start_date, lease.end_date)

    if tenant_changes:
        tenant = session.get_one(Tenant, lease.tenant_id)
        for field, value in tenant_changes.items():
            setattr(tenant, field, value)

    session.flush()
    return lease_response(session, lease)


def end_lease(session: Session, lease_id: UUID) -> LeaseResponse:
    lease = get_lease(session, lease_id)
    if lease.status == "ended":
        raise AppError(400, "Este contrato ya está terminado.", "lease_already_ended")
    lease.status = "ended"
    session.flush()
    return lease_response(session, lease)
