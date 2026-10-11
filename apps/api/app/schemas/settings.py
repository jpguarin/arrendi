from typing import Annotated

from pydantic import BaseModel, BeforeValidator, StringConstraints

from app.schemas.common import Name, OptionalText, PatchModel, blank_to_none

# Free text printed on every bill: bank, account, Nequi. It may have several lines.
PaymentDetails = Annotated[
    Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None,
    BeforeValidator(blank_to_none),
]


class SettingsUpdate(PatchModel):
    not_nullable = ("name",)

    name: Name | None = None
    document_number: OptionalText = None
    payment_details: PaymentDetails = None


class SettingsResponse(BaseModel):
    name: str
    email: str
    document_number: str | None
    payment_details: str | None
