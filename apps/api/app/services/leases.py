from datetime import date
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import AppError, conflict, not_found
from app.models import Lease, LeaseItem, Property, Tenant, Unit
from app.schemas.bill import BillItemResponse
from app.schemas.lease import (
    LeaseCreate,
    LeaseResponse,
    LeaseTerms,
    LeaseUnit,
    LeaseUpdate,
    TenantCreate,
    TenantResponse,
)
from app.services.bills import lease_items, recent_bills

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


def _replace_items(session: Session, lease: Lease, items: list[dict]) -> None:
    # One at a time per lease: whoever comes next waits here and then sees the rows this
    # transaction leaves, instead of adding its own next to them.
    session.execute(select(Lease.id).where(Lease.id == lease.id).with_for_update())
    # Out with the old ones first: the positions are unique within the lease.
    session.execute(delete(LeaseItem).where(LeaseItem.lease_id == lease.id))
    session.add_all(
        LeaseItem(owner_id=lease.owner_id, lease_id=lease.id, position=position, **item)
        for position, item in enumerate(items)
    )
    session.flush()


def _without_the_tenant(cc_emails: list[str], tenant_email: str) -> list[str]:
    """The copies of a lease: the tenant already gets every email, so not in copy too."""
    return [email for email in cc_emails if email.lower() != tenant_email.lower()]


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
        late_fee_enabled=lease.late_fee_enabled,
        late_fee_percent=lease.late_fee_percent,
        late_fee_grace_days=lease.late_fee_grace_days,
        items=[
            BillItemResponse(description=item.description, amount=item.amount)
            for item in lease_items(session, lease.id)
        ],
        auto_send=lease.auto_send,
        cc_emails=lease.cc_emails,
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
        the_tenant = Tenant(owner_id=unit.owner_id, **tenant.model_dump())
        session.add(the_tenant)
        session.flush()
        tenant_id = the_tenant.id
    else:
        found = session.get(Tenant, tenant_id)
        if found is None:
            raise not_found()
        the_tenant = found

    lease = Lease(
        owner_id=unit.owner_id,
        unit_id=unit.id,
        tenant_id=tenant_id,
        **terms.model_dump(include=set(LeaseTerms.model_fields) - {"items", "cc_emails"}),
        cc_emails=_without_the_tenant(terms.cc_emails, the_tenant.email),
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
    if terms.items:
        _replace_items(session, lease, [item.model_dump() for item in terms.items])
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
    items = changes.pop("items", None)

    for field, value in changes.items():
        setattr(lease, field, value)
    _check_dates(lease.start_date, lease.end_date)
    # Checked against what is stored: the switch and the percentage may come apart.
    if lease.late_fee_enabled and lease.late_fee_percent is None:
        raise AppError(
            422, "Escribe el porcentaje del recargo por mora.", "late_fee_percent_required"
        )

    tenant = session.get_one(Tenant, lease.tenant_id)
    for field, value in (tenant_changes or {}).items():
        setattr(tenant, field, value)
    # Also when only the tenant's address changed: it may be one of the copies.
    lease.cc_emails = _without_the_tenant(lease.cc_emails, tenant.email)

    session.flush()
    # Only the bills still to come: the ones already issued keep their own items.
    if items is not None:
        _replace_items(session, lease, items)
    return lease_response(session, lease)


def end_lease(session: Session, lease_id: UUID) -> LeaseResponse:
    lease = get_lease(session, lease_id)
    if lease.status == "ended":
        raise AppError(400, "Este contrato ya está terminado.", "lease_already_ended")
    lease.status = "ended"
    session.flush()
    return lease_response(session, lease)
