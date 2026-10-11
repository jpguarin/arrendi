from fastapi import APIRouter

from app.dependencies import CurrentUser, OwnerSession
from app.errors import ErrorResponse
from app.schemas.onboarding import OnboardingRequest, OnboardingResponse
from app.services.onboarding import complete_onboarding

router = APIRouter()


@router.post(
    "/onboarding",
    status_code=201,
    responses={401: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def onboard(
    data: OnboardingRequest, user: CurrentUser, session: OwnerSession
) -> OnboardingResponse:
    return complete_onboarding(session, user, data)
