from sqlalchemy import Engine, text
from sqlalchemy.pool import NullPool

from app.db import create_db_engine, to_psycopg_url


def test_supabase_url_uses_psycopg_driver() -> None:
    url = "postgresql://arrendi_api.ref:p%3Dword@pooler.example.com:6543/postgres"

    assert to_psycopg_url(url) == (
        "postgresql+psycopg://arrendi_api.ref:p%3Dword@pooler.example.com:6543/postgres"
    )


def test_engine_keeps_no_connections() -> None:
    engine = create_db_engine("postgresql://localhost/arrendi_test")

    assert isinstance(engine.pool, NullPool)


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
