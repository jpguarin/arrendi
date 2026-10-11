from functools import lru_cache
from uuid import UUID

from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app.config import get_settings


def to_psycopg_url(url: str) -> str:
    """Supabase gives `postgresql://` URLs; make the psycopg 3 driver explicit."""
    return make_url(url).set(drivername="postgresql+psycopg").render_as_string(hide_password=False)


def create_db_engine(url: str, keep_connections: bool = False) -> Engine:
    """An engine for Supabase's pooler in transaction mode: no prepared statements.

    By default it has no pool of its own, which is what a function that lives for one
    request needs. `keep_connections` reuses a few connections instead; see `get_engine`.
    """
    connect_args = {"prepare_threshold": None}
    if not keep_connections:
        return create_engine(to_psycopg_url(url), poolclass=NullPool, connect_args=connect_args)
    return create_engine(
        to_psycopg_url(url),
        connect_args=connect_args,
        pool_size=5,
        max_overflow=5,
        # The computer sleeps and the network changes; check before using a kept connection.
        pool_pre_ping=True,
        pool_recycle=300,
    )


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set")
    # On the developer's computer the database is far away: opening a connection takes
    # about six round trips, more than the rest of the request. Keeping connections there
    # is safe (the owner is set per transaction) and halves the wait. On Vercel the API
    # runs next to the database and a function must not hold connections between requests.
    return create_db_engine(settings.database_url, keep_connections=settings.environment == "local")


@lru_cache
def get_tasks_engine() -> Engine:
    """Connects as `arrendi_tasks`, which skips row security. Only for the daily task and
    the email provider's notices, which have no owner in the request."""
    settings = get_settings()
    if not settings.database_url_tasks:
        raise RuntimeError("DATABASE_URL_TASKS is not set")
    return create_db_engine(settings.database_url_tasks)


def set_owner_id(connection: Connection | Session, owner_id: UUID) -> None:
    """Scopes the current transaction to one owner; the row security policies read it.

    The third argument makes the value last only for this transaction. It must:
    the pooler reuses the connection for other owners' requests.
    """
    connection.execute(
        text("select set_config('app.owner_id', :owner_id, true)"),
        {"owner_id": str(owner_id)},
    )
