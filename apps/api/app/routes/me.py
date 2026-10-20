from fastapi import APIRouter

from app.dependencies import CurrentUser, OwnerSession
from app.errors import ErrorResponse
from app.schemas.owner import MeResponse
from app.services.owners import get_or_create_owner, missing_profile
from app.services.properties import has_properties

router = APIRouter()


@router.get("/me", responses={401: {"model": ErrorResponse}})
def get_me(user: CurrentUser, session: OwnerSession) -> MeResponse:
    owner = get_or_create_owner(session, user)
    return MeResponse(
        id=owner.id,
        name=owner.name,
        email=owner.email,
        onboarding_complete=has_properties(session),
        profile_complete=not missing_profile(owner),
    )
