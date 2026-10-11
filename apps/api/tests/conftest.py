from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Protocol
from uuid import UUID, uuid4

import jwt
import pytest
from alembic import command
from alembic.config import Config
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.ec import (
    EllipticCurvePrivateKey,
    EllipticCurvePublicKey,
)
from fastapi.testclient import TestClient
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import Connection, Engine, text
from sqlalchemy.engine import make_url

from app.auth import TokenVerifier
from app.db import create_db_engine
from app.dependencies import get_db_engine, get_token_verifier
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


# Supabase creates these roles and lets them use every new table in `public`.
# The test database imitates that, so the migrations have something to revoke.
SUPABASE_ROLES = ("anon", "authenticated", "service_role")
APP_ROLES = ("arrendi_api", "arrendi_tasks")
ROLE_PASSWORD = "arrendi_test"


def create_role_if_missing(connection: Connection, role: str) -> None:
    exists = connection.execute(
        text("select 1 from pg_roles where rolname = :role"), {"role": role}
    ).first()
    if not exists:
        connection.execute(text(f"create role {role} nologin"))


@pytest.fixture(scope="session")
def admin_engine(admin_url: str) -> Iterator[Engine]:
    """Empties the test database and applies every migration to it."""
    engine = create_db_engine(admin_url)
    with engine.begin() as connection:
        connection.execute(text("drop schema public cascade"))
        connection.execute(text("create schema public"))
        for role in SUPABASE_ROLES:
            create_role_if_missing(connection, role)
            connection.execute(text(f"grant usage on schema public to {role}"))
            connection.execute(
                text(f"alter default privileges in schema public grant all on tables to {role}")
            )
    command.upgrade(alembic_config(admin_url), "head")
    # The migration creates the app roles without login; each environment enables it by hand.
    with engine.begin() as connection:
        for role in APP_ROLES:
            connection.execute(text(f"alter role {role} with login password '{ROLE_PASSWORD}'"))
    yield engine
    engine.dispose()


def engine_as(admin_url: str, role: str) -> Engine:
    return create_db_engine(
        make_url(admin_url)
        .set(username=role, password=ROLE_PASSWORD)
        .render_as_string(hide_password=False)
    )


@pytest.fixture(scope="session")
def api_engine(admin_engine: Engine, admin_url: str) -> Iterator[Engine]:
    """Connects like the API does for an owner's request: subject to the policies."""
    engine = engine_as(admin_url, "arrendi_api")
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def tasks_engine(admin_engine: Engine, admin_url: str) -> Iterator[Engine]:
    """Connects like the daily task does: bypasses the policies."""
    engine = engine_as(admin_url, "arrendi_tasks")
    yield engine
    engine.dispose()


@pytest.fixture
def two_owners(admin_engine: Engine) -> Iterator[tuple[UUID, UUID]]:
    """Two owners, each with a row, created by the admin (who bypasses the policies)."""
    ana, beto = uuid4(), uuid4()
    with admin_engine.begin() as connection:
        connection.execute(
            text("insert into owners (id, name, email) values (:id, :name, :email)"),
            [
                {"id": ana, "name": "Ana", "email": "ana@example.com"},
                {"id": beto, "name": "Beto", "email": "beto@example.com"},
            ],
        )
    yield ana, beto
    with admin_engine.begin() as connection:
        connection.execute(text("delete from owners where id in (:ana, :beto)"), locals())


ISSUER = "https://test-project.supabase.co/auth/v1"


class FakeJwksClient:
    """Stands in for Supabase's JWKS endpoint: always answers with one public key."""

    def __init__(self, public_key: EllipticCurvePublicKey) -> None:
        self.public_key = public_key

    def get_signing_key_from_jwt(self, token: str) -> SimpleNamespace:
        return SimpleNamespace(key=self.public_key)


@pytest.fixture(scope="session")
def signing_key() -> EllipticCurvePrivateKey:
    return ec.generate_private_key(ec.SECP256R1())


@pytest.fixture(scope="session")
def token_verifier(signing_key: EllipticCurvePrivateKey) -> TokenVerifier:
    return TokenVerifier(issuer=ISSUER, jwks_client=FakeJwksClient(signing_key.public_key()))


class MakeToken(Protocol):
    def __call__(
        self, owner_id: UUID | str, key: object = ..., algorithm: str = ..., **claims: object
    ) -> str: ...


@pytest.fixture
def make_token(signing_key: EllipticCurvePrivateKey) -> MakeToken:
    """Signs an access token like the ones Supabase Auth issues."""

    def make(
        owner_id: UUID | str,
        key: object = signing_key,
        algorithm: str = "ES256",
        **claims: object,
    ) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": str(owner_id),
            "iss": ISSUER,
            "aud": "authenticated",
            "exp": now + timedelta(hours=1),
            "iat": now,
            "email": "ana@example.com",
            "user_metadata": {"full_name": "Ana Gómez"},
            "is_anonymous": False,
        } | claims
        return jwt.encode(payload, key, algorithm=algorithm)

    return make


@pytest.fixture
def api(api_engine: Engine, token_verifier: TokenVerifier) -> Iterator[TestClient]:
    """The real app, connected to the test database and trusting the test signing key."""
    app.dependency_overrides[get_db_engine] = lambda: api_engine
    app.dependency_overrides[get_token_verifier] = lambda: token_verifier
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def new_user_ids(admin_engine: Engine) -> Iterator[tuple[UUID, UUID]]:
    """Ids of two users who have signed up in Supabase but never called the API."""
    ids = (uuid4(), uuid4())
    yield ids
    with admin_engine.begin() as connection:
        connection.execute(text("delete from owners where id = any(:ids)"), {"ids": list(ids)})


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
