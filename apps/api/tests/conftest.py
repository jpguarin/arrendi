from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import Engine, text
from sqlalchemy.engine import make_url

from app.db import create_db_engine
from app.main import app

API_DIR = Path(__file__).resolve().parent.parent
LOCAL_HOSTS = {None, "localhost", "127.0.0.1", "::1"}


class TestSettings(BaseSettings):
    __test__ = False
    model_config = SettingsConfigDict(env_file=API_DIR / ".env", extra="ignore")

    test_database_url: str = "postgresql://localhost:5432/arrendi_test"


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="session")
def admin_url() -> str:
    """URL of the local test database, as a user that can create roles."""
    url = TestSettings().test_database_url
    if make_url(url).host not in LOCAL_HOSTS:
        raise RuntimeError("TEST_DATABASE_URL must point to a local PostgreSQL, never to Supabase")
    return url


def alembic_config(url: str) -> Config:
    config = Config(API_DIR / "alembic.ini")
    config.set_main_option("script_location", str(API_DIR / "migrations"))
    config.attributes["url"] = url
    config.attributes["configure_logging"] = False
    return config


@pytest.fixture(scope="session")
def admin_engine(admin_url: str) -> Iterator[Engine]:
    """Empties the test database and applies every migration to it."""
    engine = create_db_engine(admin_url)
    with engine.begin() as connection:
        connection.execute(text("drop schema public cascade"))
        connection.execute(text("create schema public"))
    command.upgrade(alembic_config(admin_url), "head")
    yield engine
    engine.dispose()
