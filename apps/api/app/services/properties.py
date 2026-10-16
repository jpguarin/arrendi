from collections import defaultdict
from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.errors import not_found
from app.models import Bill, Lease, Property, Tenant, Unit
from app.schemas.property import (
    ActiveLeaseSummary,
    PropertyCreate,
    PropertyResponse,
    PropertyUpdate,
    UnitCreate,
    UnitResponse,
    UnitUpdate,
)

# Every query here runs inside the owner's transaction: row security already limits it to
# their rows, so another owner's id simply finds nothing.


def has_properties(session: Session) -> bool:
    return bool(session.scalar(select(exists(select(Property.id)))))


def _unit_responses(session: Session, units: list[Unit]) -> list[UnitResponse]:
    active_leases = {
        lease.unit_id: ActiveLeaseSummary(id=lease.id, tenant_name=tenant_name, rent=lease.rent)
        for lease, tenant_name in session.execute(
            select(Lease, Tenant.name)
            .join(Tenant, Tenant.id == Lease.tenant_id)
            .where(Lease.unit_id.in_([unit.id for unit in units]), Lease.status == "active")
        )
    }
    # What each active lease still owes says how its unit is doing.
    owing: dict[UUID, set[str]] = defaultdict(set)
    for lease_id, bill_status in session.execute(
        select(Bill.lease_id, Bill.status)
        .where(
            Bill.lease_id.in_([lease.id for lease in active_leases.values()]),
            Bill.status.in_(("overdue", "partial")),
        )
        .distinct()
    ):
        owing[lease_id].add(bill_status)

    def status_of(unit: Unit) -> str:
        lease = active_leases.get(unit.id)
        if lease is None:
            return "vacant"
        if "overdue" in owing[lease.id]:
            return "overdue"
        return "partial" if "partial" in owing[lease.id] else "up_to_date"

    return [
        UnitResponse(
            id=unit.id,
            property_id=unit.property_id,
            name=unit.name,
            use=unit.use,
            status=status_of(unit),
            active_lease=active_leases.get(unit.id),
        )
        for unit in units
    ]


def _property_responses(session: Session, properties: list[Property]) -> list[PropertyResponse]:
    units = session.scalars(
        select(Unit)
        .where(Unit.property_id.in_([p.id for p in properties]))
        .order_by(Unit.created_at, Unit.id)
    ).all()
    units_by_property: dict[UUID, list[UnitResponse]] = defaultdict(list)
    for unit in _unit_responses(session, list(units)):
        units_by_property[unit.property_id].append(unit)
    return [
        PropertyResponse(
            id=p.id,
            name=p.name,
            address=p.address,
            city=p.city,
            country=p.country,
            type=p.type,
            units=units_by_property[p.id],
        )
        for p in properties
    ]


def property_response(session: Session, found: Property) -> PropertyResponse:
    return _property_responses(session, [found])[0]


def list_properties(session: Session) -> list[PropertyResponse]:
    properties = session.scalars(select(Property).order_by(Property.created_at, Property.id))
    return _property_responses(session, list(properties))


def create_property(session: Session, owner_id: UUID, data: PropertyCreate) -> PropertyResponse:
    new = Property(owner_id=owner_id, **data.model_dump())
    session.add(new)
    session.flush()
    return property_response(session, new)


def _get_property(session: Session, property_id: UUID) -> Property:
    found = session.get(Property, property_id)
    if found is None:
        raise not_found()
    return found


def update_property(session: Session, property_id: UUID, data: PropertyUpdate) -> PropertyResponse:
    found = _get_property(session, property_id)
    for field, value in data.changes().items():
        setattr(found, field, value)
    session.flush()
    return property_response(session, found)


def add_unit(session: Session, property_id: UUID, data: UnitCreate) -> UnitResponse:
    parent = _get_property(session, property_id)
    unit = Unit(owner_id=parent.owner_id, property_id=parent.id, **data.model_dump())
    session.add(unit)
    session.flush()
    return _unit_responses(session, [unit])[0]


def update_unit(session: Session, unit_id: UUID, data: UnitUpdate) -> UnitResponse:
    unit = session.get(Unit, unit_id)
    if unit is None:
        raise not_found()
    for field, value in data.changes().items():
        setattr(unit, field, value)
    session.flush()
    return _unit_responses(session, [unit])[0]
