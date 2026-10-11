from uuid import UUID

from pydantic import BaseModel


class MeResponse(BaseModel):
    id: UUID
    name: str
    email: str
    onboarding_complete: bool
