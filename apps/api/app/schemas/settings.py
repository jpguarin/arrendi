from typing import Annotated

from pydantic import BaseModel, BeforeValidator, Field, StringConstraints

from app.schemas.common import DocumentType, Name, OptionalText, PatchModel, blank_to_none

# Free text printed on every bill: bank, account, Nequi. It may have several lines.
PaymentDetails = Annotated[
    Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None,
    BeforeValidator(blank_to_none),
]


# The day of the month the bills go out. Up to 28, so it exists in every month.
SendDay = Annotated[int, Field(strict=True, ge=1, le=28)]


class SettingsUpdate(PatchModel):
    not_nullable = ("name", "document_type", "send_day", "reminder_1", "reminder_2", "email_copy")

    name: Name | None = None
    document_type: DocumentType | None = None
    document_number: OptionalText = None
    payment_details: PaymentDetails = None
    send_day: SendDay | None = None
    reminder_1: bool | None = None
    reminder_2: bool | None = None
    email_copy: bool | None = None


class SettingsResponse(BaseModel):
    name: str
    email: str
    document_type: DocumentType
    document_number: str | None
    payment_details: str | None
    send_day: int
    # The reminders the day after the due date and seven days after it.
    reminder_1: bool
    reminder_2: bool
    # Whether the owner gets a copy of every email.
    email_copy: bool
