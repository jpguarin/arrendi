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


def create_db_engine(url: str) -> Engine:
    # The API runs in functions behind Supabase's pooler in transaction mode:
    # no pool of our own, and no prepared statements.
    return create_engine(
        to_psycopg_url(url),
        poolclass=NullPool,
        connect_args={"prepare_threshold": None},
    )


@lru_cache
def get_engine() -> Engine:
    url = get_settings().database_url
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    return create_db_engine(url)


def set_owner_id(connection: Connection | Session, owner_id: UUID) -> None:
    """Scopes the current transaction to one owner; the row security policies read it.

    The third argument makes the value last only for this transaction. It must:
    the pooler reuses the connection for other owners' requests.
    """
    connection.execute(
        text("select set_config('app.owner_id', :owner_id, true)"),
        {"owner_id": str(owner_id)},
    )
