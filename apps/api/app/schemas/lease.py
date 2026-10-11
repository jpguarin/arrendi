from datetime import date, datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import Email, Name, OptionalText, PatchModel, Pesos, PositivePesos
from app.schemas.property import UnitUse

LeaseStatus = Literal["active", "ended"]
# Provisional: 29 to 31 are left out so the day exists in every month.
DueDay = Annotated[int, Field(strict=True, ge=1, le=28)]


class TenantCreate(BaseModel):
    name: Name
    email: Email
    document_number: OptionalText = None
    phone: OptionalText = None


class TenantUpdate(PatchModel):
    not_nullable = ("name", "email")

    name: Name | None = None
    email: Email | None = None
    document_number: OptionalText = None
    phone: OptionalText = None


class LeaseTerms(BaseModel):
    rent: PositivePesos
    due_day: DueDay
    start_date: date
    end_date: date | None = None
    deposit: Pesos | None = None
    auto_send: bool = True


class LeaseCreate(LeaseTerms):
    unit_id: UUID
    # Exactly one of the two: a new tenant, or one the owner already has.
    tenant: TenantCreate | None = None
    tenant_id: UUID | None = None

    @model_validator(mode="after")
    def _one_tenant(self) -> Self:
        if (self.tenant is None) == (self.tenant_id is None):
            raise ValueError("send either tenant or tenant_id")
        return self


class LeaseUpdate(PatchModel):
    not_nullable = ("rent", "due_day", "start_date", "auto_send", "tenant")

    rent: PositivePesos | None = None
    due_day: DueDay | None = None
    start_date: date | None = None
    end_date: date | None = None
    deposit: Pesos | None = None
    auto_send: bool | None = None
    tenant: TenantUpdate | None = None


class LeaseUnit(BaseModel):
    id: UUID
    name: str
    use: UnitUse
    property_id: UUID
    property_name: str


class TenantResponse(BaseModel):
    id: UUID
    name: str
    email: str
    document_number: str | None
    phone: str | None


class LeaseResponse(BaseModel):
    id: UUID
    status: LeaseStatus
    rent: int
    due_day: int
    start_date: date
    end_date: date | None
    deposit: int | None
    auto_send: bool
    # The signed lease, if the owner uploaded it. The file itself is behind its own route.
    document_name: str | None
    document_uploaded_at: datetime | None
    unit: LeaseUnit
    tenant: TenantResponse
