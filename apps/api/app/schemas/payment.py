from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import PositivePesos

PaymentMethod = Literal["transfer", "nequi", "cash", "other"]


class PaymentCreate(BaseModel):
    amount: PositivePesos
    payment_date: date
    method: PaymentMethod
    # Whether the tenant gets a receipt by email.
    send_receipt: bool = False


class PaymentResponse(BaseModel):
    id: UUID
    payment_date: date
    amount: int
    method: PaymentMethod
    # The proof itself is behind its own route.
    has_proof: bool
    created_at: datetime
