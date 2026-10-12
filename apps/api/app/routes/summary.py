from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from app.dependencies import OwnerSession, Today
from app.errors import ErrorResponse
from app.schemas.summary import SummaryResponse
from app.services.summary import get_summary

router = APIRouter(responses={401: {"model": ErrorResponse}})

Month = Annotated[str | None, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")]


@router.get("/summary")
def summary(session: OwnerSession, today: Today, month: Month = None) -> SummaryResponse:
    """The home screen. Without `month` (`AAAA-MM`), the current month in Colombia."""
    first_day = date.fromisoformat(f"{month}-01") if month else today.replace(day=1)
    return get_summary(session, first_day)
