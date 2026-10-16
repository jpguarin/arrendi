from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import Name, OptionalText, PatchModel
from app.schemas.countries import DEFAULT_COUNTRY, Country

PropertyType = Literal["house", "building", "apartment", "shop"]
UnitUse = Literal["residential", "commercial"]
# Until stage 5 a unit is only vacant or not; `overdue` and `partial` come with the bills.
UnitStatus = Literal["vacant", "up_to_date", "partial", "overdue"]


class UnitCreate(BaseModel):
    name: Name
    use: UnitUse


class UnitUpdate(PatchModel):
    not_nullable = ("name", "use")

    name: Name | None = None
    use: UnitUse | None = None


class ActiveLeaseSummary(BaseModel):
    id: UUID
    tenant_name: str
    rent: int


class UnitResponse(BaseModel):
    id: UUID
    property_id: UUID
    name: str
    use: UnitUse
    status: UnitStatus
    active_lease: ActiveLeaseSummary | None


class PropertyCreate(BaseModel):
    name: Name
    address: OptionalText = None
    city: OptionalText = None
    country: Country = DEFAULT_COUNTRY
    type: PropertyType


class PropertyUpdate(PatchModel):
    not_nullable = ("name", "type", "country")

    name: Name | None = None
    address: OptionalText = None
    city: OptionalText = None
    country: Country | None = None
    type: PropertyType | None = None


class PropertyResponse(BaseModel):
    id: UUID
    name: str
    address: str | None
    city: str | None
    country: Country
    type: PropertyType
    units: list[UnitResponse]
