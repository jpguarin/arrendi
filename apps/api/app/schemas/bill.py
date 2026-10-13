from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

from app.schemas.common import DocumentType, PaymentDetails, PositivePesos
from app.schemas.payment import PaymentMethod, PaymentResponse

BillStatus = Literal["pending", "partial", "paid", "overdue", "voided"]
BillOrigin = Literal["monthly", "manual"]
# `receivable` gathers pending, partial and overdue: what is still owed.
BillStatusFilter = Literal["receivable", "paid", "voided"]

Description = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


# A bill fits on one page; the monthly one adds the rent and the deposit to these.
MAX_ITEMS = 10


class ItemInput(BaseModel):
    """Something charged: what it is and how much. A bill is the sum of these."""

    description: Description
    amount: PositivePesos


class BillCreate(BaseModel):
    """A manual bill: one or more extra charges on a lease, apart from the monthly rent."""

    lease_id: UUID
    # In the order the bill shows them. The total is their sum.
    items: Annotated[list[ItemInput], Field(min_length=1, max_length=MAX_ITEMS)]
    # One for the whole bill, not one per item.
    due_date: date
    # Only for this bill. Left out, it takes the lease's, and then the owner's.
    payment_details: PaymentDetails = None


class BillSummary(BaseModel):
    id: UUID
    number: int
    origin: BillOrigin
    # First day of the month being billed; null in manual bills.
    period: date | None
    issue_date: date
    due_date: date
    total: int
    # Never stored: the total minus what has been paid.
    balance: int
    status: BillStatus
    # The latest payment, if any: when it was made and how.
    last_payment_date: date | None
    last_payment_method: PaymentMethod | None
    lease_id: UUID
    unit_id: UUID
    unit_name: str
    tenant_name: str


class BillItemResponse(BaseModel):
    description: str
    amount: int


class BillIssuer(BaseModel):
    """The owner, as the bill shows them."""

    name: str
    document_type: DocumentType
    document_number: str | None
    # The ones the bill was issued with, not the owner's as they are now.
    payment_details: str | None


# Where the late fee of a bill stands. `on_time`: not late yet, or paid in time. `pending`:
# late, to be charged by the next monthly bill. `waived`: the owner let it go. `charged`:
# it is an item of another bill.
LateFeeStatus = Literal["on_time", "pending", "waived", "charged"]


class LateFeeCharge(BaseModel):
    """The bill that charged a late fee."""

    id: UUID
    number: int


class LateFee(BaseModel):
    """What paying this bill late costs, as it said when it was issued."""

    amount: int
    # The last day to pay it in full without the fee.
    deadline: date
    status: LateFeeStatus
    charged_on: LateFeeCharge | None


NotificationType = Literal[
    "bill", "reminder_1", "reminder_2", "receipt", "manual_reminder", "resend"
]
DeliveryStatus = Literal["pending", "sent", "bounced", "failed"]


class NotificationResponse(BaseModel):
    id: UUID
    type: NotificationType
    recipient: str
    # `pending` until the email goes out, right after the request that asked for it.
    delivery_status: DeliveryStatus
    created_at: datetime
    sent_at: datetime | None


class BillResponse(BillSummary):
    items: list[BillItemResponse]
    property_name: str
    tenant_document_type: DocumentType
    tenant_document_number: str | None
    issuer: BillIssuer
    # Whether it was issued with the owner's signature. Without it, the PDF leaves a line
    # to sign by hand.
    signed: bool
    # Null if the bill was issued without a late fee, is a manual one, or is voided.
    late_fee: LateFee | None
    created_at: datetime
    voided_at: datetime | None
    # Both newest first.
    payments: list[PaymentResponse]
    notifications: list[NotificationResponse]
