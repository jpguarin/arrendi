from collections.abc import Iterator
from datetime import date
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.auth import AuthUnavailableError, AuthUser, InvalidTokenError, TokenVerifier
from app.config import get_settings
from app.dates import today_in_bogota
from app.db import get_engine, get_tasks_engine, set_owner_id
from app.email.sender import EmailSender, build_sender
from app.errors import auth_unavailable, unauthorized
from app.storage import Storage, SupabaseStorage

bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache
def get_token_verifier() -> TokenVerifier:
    supabase_url = get_settings().supabase_url
    if not supabase_url:
        raise RuntimeError("SUPABASE_URL is not set")
    return TokenVerifier.for_supabase(supabase_url)


@lru_cache
def get_storage() -> Storage:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_secret_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SECRET_KEY are not set")
    return SupabaseStorage(
        settings.supabase_url, settings.supabase_secret_key, settings.storage_bucket
    )


FileStorage = Annotated[Storage, Depends(get_storage)]


@lru_cache
def get_email_sender() -> EmailSender:
    return build_sender(get_settings())


Mailer = Annotated[EmailSender, Depends(get_email_sender)]


# The business date of the request. A dependency so the tests can pick the day.
Today = Annotated[date, Depends(today_in_bogota)]


def get_db_engine() -> Engine:
    return get_engine()


def get_tasks_db_engine() -> Engine:
    return get_tasks_engine()


def get_bearer_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> str:
    if credentials is None:
        raise unauthorized()
    return credentials.credentials


def get_current_user(
    # Order matters: a request without a token is rejected before anything else is set up.
    token: Annotated[str, Depends(get_bearer_token)],
    verifier: Annotated[TokenVerifier, Depends(get_token_verifier)],
) -> AuthUser:
    try:
        return verifier.verify(token)
    except InvalidTokenError as error:
        raise unauthorized() from error
    except AuthUnavailableError as error:
        raise auth_unavailable() from error


CurrentUser = Annotated[AuthUser, Depends(get_current_user)]


def get_owner_session(
    user: CurrentUser, engine: Annotated[Engine, Depends(get_db_engine)]
) -> Iterator[Session]:
    """One transaction per request, scoped to the owner in the token.

    It commits when the route returns and rolls back if it raises.
    """
    with Session(engine) as session, session.begin():
        set_owner_id(session, user.owner_id)
        yield session


# `scope="function"` commits before the response is sent, so a failed commit is an error
# response and anything done after the request (like sending email) sees committed data.
OwnerSession = Annotated[Session, Depends(get_owner_session, scope="function")]
