import pytest
from sqlalchemy import Engine, text
from sqlalchemy.pool import NullPool, QueuePool

from app.config import Settings
from app.db import create_db_engine, get_engine, to_psycopg_url


def test_supabase_url_uses_psycopg_driver() -> None:
    url = "postgresql://arrendi_api.ref:p%3Dword@pooler.example.com:6543/postgres"

    assert to_psycopg_url(url) == (
        "postgresql+psycopg://arrendi_api.ref:p%3Dword@pooler.example.com:6543/postgres"
    )


def test_engine_connects_without_prepared_statements(admin_engine: Engine) -> None:
    with admin_engine.connect() as connection:
        for _ in range(10):
            assert connection.execute(text("select 1")).scalar_one() == 1
        prepared = connection.execute(text("select count(*) from pg_prepared_statements"))
        assert prepared.scalar_one() == 0


def test_migrations_apply_on_an_empty_database(admin_engine: Engine) -> None:
    with admin_engine.connect() as connection:
        tables = connection.execute(
            text("select tablename from pg_tables where schemaname = 'public'")
        ).scalars()
        assert "alembic_version" in set(tables)


def test_engine_keeps_no_connections_by_default() -> None:
    engine = create_db_engine("postgresql://user:secret@localhost:5432/arrendi")

    assert isinstance(engine.pool, NullPool)


def test_engine_can_keep_connections(admin_url: str) -> None:
    engine = create_db_engine(admin_url, keep_connections=True)

    assert isinstance(engine.pool, QueuePool)
    backends = set()
    for _ in range(3):
        with engine.connect() as connection:
            for _ in range(10):
                connection.execute(text("select 1"))
            backends.add(connection.execute(text("select pg_backend_pid()")).scalar_one())
            # Still no prepared statements: it goes through the pooler all the same.
            prepared = connection.execute(text("select count(*) from pg_prepared_statements"))
            assert prepared.scalar_one() == 0
    engine.dispose()

    assert len(backends) == 1


@pytest.mark.parametrize(
    ("environment", "pool"),
    [("local", QueuePool), ("preview", NullPool), ("production", NullPool)],
)
def test_only_the_local_api_keeps_connections(
    monkeypatch: pytest.MonkeyPatch, environment: str, pool: type
) -> None:
    """A function on Vercel must not hold connections between requests."""
    settings = Settings(
        environment=environment, database_url="postgresql://user:secret@localhost:5432/arrendi"
    )
    monkeypatch.setattr("app.db.get_settings", lambda: settings)
    get_engine.cache_clear()

    try:
        assert isinstance(get_engine().pool, pool)
    finally:
        get_engine.cache_clear()
