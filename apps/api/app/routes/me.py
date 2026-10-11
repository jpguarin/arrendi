from fastapi import APIRouter

from app.dependencies import CurrentUser, OwnerSession
from app.errors import ErrorResponse
from app.schemas.owner import MeResponse
from app.services.owners import get_or_create_owner

router = APIRouter()


@router.get("/me", responses={401: {"model": ErrorResponse}})
def get_me(user: CurrentUser, session: OwnerSession) -> MeResponse:
    owner = get_or_create_owner(session, user)
    return MeResponse(
        id=owner.id,
        name=owner.name,
        email=owner.email,
        # Stage 1 has no properties yet; this is computed from stage 2 on.
        onboarding_complete=False,
    )
