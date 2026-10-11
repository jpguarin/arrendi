from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
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
