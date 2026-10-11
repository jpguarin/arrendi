from typing import Annotated, Self

from pydantic import BaseModel, Field, model_validator

from app.schemas.lease import LeaseResponse, LeaseTerms, TenantCreate
from app.schemas.property import PropertyCreate, PropertyResponse, UnitCreate


class OnboardingLease(LeaseTerms):
    # Position of the unit in `units`: the units do not have ids yet.
    unit_index: Annotated[int, Field(strict=True, ge=0)]
    tenant: TenantCreate


class OnboardingRequest(BaseModel):
    property: PropertyCreate
    units: Annotated[list[UnitCreate], Field(min_length=1, max_length=50)]
    # The third step can be skipped.
    lease: OnboardingLease | None = None

    @model_validator(mode="after")
    def _lease_points_at_a_unit(self) -> Self:
        if self.lease is not None and self.lease.unit_index >= len(self.units):
            raise ValueError("unit_index is out of range")
        return self


class OnboardingResponse(BaseModel):
    property: PropertyResponse
    lease: LeaseResponse | None
