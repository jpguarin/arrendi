from uuid import UUID

from pydantic import BaseModel


class MeResponse(BaseModel):
    id: UUID
    name: str
    email: str
    onboarding_complete: bool
    # Whether the owner's data a bill needs is filled in: a new owner does it first.
    profile_complete: bool
