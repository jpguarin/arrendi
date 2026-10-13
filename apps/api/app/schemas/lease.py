from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.bill import MAX_ITEMS, BillItemResponse, BillSummary, ItemInput
from app.schemas.common import (
    DocumentType,
    Email,
    Name,
    OptionalText,
    PatchModel,
    PaymentDetails,
    Pesos,
    PositivePesos,
)
from app.schemas.property import UnitUse

LeaseStatus = Literal["active", "ended"]
# Provisional: 29 to 31 are left out so the day exists in every month.
DueDay = Annotated[int, Field(strict=True, ge=1, le=28)]


# What the lease charges every month besides the rent, like the building fee.
LeaseItems = Annotated[list[ItemInput], Field(max_length=MAX_ITEMS)]


# The late fee: a percentage of the rent, with up to two decimals, and the days after the
# due date before it applies.
LateFeePercent = Annotated[Decimal, Field(gt=0, le=100, max_digits=5, decimal_places=2)]
GraceDays = Annotated[int, Field(strict=True, ge=0, le=30)]


class TenantCreate(BaseModel):
    name: Name
    email: Email
    document_type: DocumentType = "cc"
    document_number: OptionalText = None
    phone: OptionalText = None


class TenantUpdate(PatchModel):
    not_nullable = ("name", "email", "document_type")

    name: Name | None = None
    email: Email | None = None
    document_type: DocumentType | None = None
    document_number: OptionalText = None
    phone: OptionalText = None


class LeaseTerms(BaseModel):
    rent: PositivePesos
    due_day: DueDay
    start_date: date
    end_date: date | None = None
    deposit: Pesos | None = None
    # The first monthly bill charges the deposit, unless the tenant already paid it.
    charge_deposit: bool = True
    # Every monthly bill charges these after the rent, in this order.
    items: LeaseItems = []
    auto_send: bool = True
    # Paying the rent late costs this percentage of it, once, in the next monthly bill.
    late_fee_enabled: bool = False
    late_fee_percent: LateFeePercent | None = None
    late_fee_grace_days: GraceDays = 0

    @model_validator(mode="after")
    def _late_fee_has_its_percentage(self) -> Self:
        if self.late_fee_enabled and self.late_fee_percent is None:
            raise ValueError("late_fee_percent is required when the late fee is on")
        return self

    # How to pay the bills of this lease. Left out, they take the owner's.
    payment_details: PaymentDetails = None


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
    not_nullable = (
        "rent",
        "due_day",
        "start_date",
        "charge_deposit",
        "items",
        "auto_send",
        "late_fee_enabled",
        "late_fee_grace_days",
        "tenant",
    )

    rent: PositivePesos | None = None
    due_day: DueDay | None = None
    start_date: date | None = None
    end_date: date | None = None
    deposit: Pesos | None = None
    charge_deposit: bool | None = None
    # Sent, it replaces the whole list; an empty one removes them all.
    items: LeaseItems | None = None
    auto_send: bool | None = None
    late_fee_enabled: bool | None = None
    late_fee_percent: LateFeePercent | None = None
    late_fee_grace_days: GraceDays | None = None
    payment_details: PaymentDetails = None
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
    document_type: DocumentType
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
    # Only the first monthly bill charges it; after that this changes nothing.
    charge_deposit: bool
    # What every monthly bill charges after the rent, in order.
    items: list[BillItemResponse]
    auto_send: bool
    late_fee_enabled: bool
    # Kept when the late fee is turned off, to turn it back on as it was.
    late_fee_percent: Decimal | None
    late_fee_grace_days: int
    # The lease's own, if it has them; null means its bills take the owner's.
    payment_details: str | None
    # The signed lease, if the owner uploaded it. The file itself is behind its own route.
    document_name: str | None
    document_uploaded_at: datetime | None
    unit: LeaseUnit
    tenant: TenantResponse
    # The latest ones, newest first, voided ones too.
    recent_bills: list[BillSummary]
