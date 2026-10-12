from datetime import date
from uuid import UUID

from pydantic import BaseModel

from app.schemas.bill import BillSummary


class BouncedEmail(BaseModel):
    """A bill whose email came back: the tenant's address is probably wrong."""

    bill_id: UUID
    number: int
    unit_name: str
    tenant_name: str
    recipient: str


class SummaryResponse(BaseModel):
    # First day of the month the figures are about.
    month: date
    # Of the bills of that month: what they add up to, what has been paid on them, and
    # the difference.
    expected: int
    collected: int
    pending: int
    # Still owed on bills of earlier months. Not part of the figures above.
    previous_pending: int
    units_total: int
    units_overdue: int
    # Everything still owed, of any month, overdue first.
    receivable: list[BillSummary]
    # The paid bills of the month.
    paid: list[BillSummary]
    bounced: list[BouncedEmail]
