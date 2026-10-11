"""The dependency that validates Supabase's token and scopes the transaction to its owner."""

import hmac
import json
from base64 import urlsafe_b64encode
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePrivateKey
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jwt.exceptions import PyJWKClientConnectionError
from sqlalchemy import Engine, text

from app.auth import TokenVerifier
from app.dependencies import CurrentUser, OwnerSession, get_db_engine, get_token_verifier
from app.errors import AppError, register_error_handlers
from tests.conftest import ISSUER, MakeToken, bearer

UNAUTHORIZED = {"detail": "Tu sesión no es válida. Vuelve a ingresar.", "code": "unauthorized"}


@pytest.fixture
def sample_app(api_engine: Engine, token_verifier: TokenVerifier) -> FastAPI:
    sample = FastAPI()
    register_error_handlers(sample)
    sample.dependency_overrides[get_db_engine] = lambda: api_engine
    sample.dependency_overrides[get_token_verifier] = lambda: token_verifier

    @sample.get("/user")
    def read_user(user: CurrentUser) -> dict[str, str | None]:
        return {"owner_id": str(user.owner_id), "email": user.email, "name": user.name}

    @sample.get("/names")
    def read_names(session: OwnerSession) -> dict[str, object]:
        return {
            "owner_id": session.execute(
                text("select current_setting('app.owner_id', true)")
            ).scalar_one(),
            "names": session.execute(text("select name from owners")).scalars().all(),
        }

    @sample.post("/rename")
    def rename(session: OwnerSession, fail: bool = False) -> dict[str, bool]:
        session.execute(text("update owners set name = 'Renombrada'"))
        if fail:
            raise AppError(400, "No se pudo.", "rename_failed")
        return {"ok": True}

    return sample


@pytest.fixture
def api(sample_app: FastAPI) -> Iterator[TestClient]:
    with TestClient(sample_app) as client:
        yield client


def name_of(admin_engine: Engine, owner_id: UUID) -> str:
    with admin_engine.connect() as connection:
        return connection.execute(
            text("select name from owners where id = :id"), {"id": owner_id}
        ).scalar_one()


def test_valid_token_gives_the_user(api: TestClient, make_token: MakeToken) -> None:
    owner_id = uuid4()

    response = api.get("/user", headers=bearer(make_token(owner_id)))

    assert response.status_code == 200
    assert response.json() == {
        "owner_id": str(owner_id),
        "email": "ana@example.com",
        "name": "Ana Gómez",
    }


def test_name_falls_back_to_the_name_claim(api: TestClient, make_token: MakeToken) -> None:
    token = make_token(uuid4(), user_metadata={"name": "Ana G."})

    assert api.get("/user", headers=bearer(token)).json()["name"] == "Ana G."


def test_name_is_optional(api: TestClient, make_token: MakeToken) -> None:
    token = make_token(uuid4(), user_metadata={})

    assert api.get("/user", headers=bearer(token)).json()["name"] is None


def test_missing_token_is_rejected(api: TestClient) -> None:
    response = api.get("/user")

    assert response.status_code == 401
    assert response.json() == UNAUTHORIZED


@pytest.mark.parametrize(
    "headers",
    [
        {"Authorization": "Bearer not-a-token"},
        {"Authorization": "Bearer "},
        {"Authorization": "Basic abc"},
    ],
)
def test_malformed_token_is_rejected(api: TestClient, headers: dict[str, str]) -> None:
    response = api.get("/user", headers=headers)

    assert response.status_code == 401
    assert response.json() == UNAUTHORIZED


def test_expired_token_is_rejected(api: TestClient, make_token: MakeToken) -> None:
    token = make_token(uuid4(), exp=datetime.now(UTC) - timedelta(minutes=1))

    assert api.get("/user", headers=bearer(token)).status_code == 401


def test_token_signed_with_another_key_is_rejected(api: TestClient, make_token: MakeToken) -> None:
    token = make_token(uuid4(), key=ec.generate_private_key(ec.SECP256R1()))

    assert api.get("/user", headers=bearer(token)).status_code == 401


def test_token_signed_with_the_public_key_as_secret_is_rejected(
    api: TestClient, make_token: MakeToken, signing_key: EllipticCurvePrivateKey
) -> None:
    """Algorithm confusion: the public key is public, so it must never work as an HS256 secret."""
    secret = signing_key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    # Built by hand: PyJWT refuses to sign with a public key as the secret.
    _, payload, _ = make_token(uuid4()).split(".")
    header = urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).rstrip(b"=")
    signed = header + b"." + payload.encode()
    signature = urlsafe_b64encode(hmac.digest(secret, signed, "sha256")).rstrip(b"=")
    token = (signed + b"." + signature).decode()

    assert api.get("/user", headers=bearer(token)).status_code == 401


@pytest.mark.parametrize(
    "claims",
    [
        {"iss": "https://other-project.supabase.co/auth/v1"},
        {"aud": "anon"},
        {"sub": "not-a-uuid"},
        {"is_anonymous": True},
    ],
    ids=["other issuer", "other audience", "sub is not a uuid", "anonymous user"],
)
def test_token_with_wrong_claims_is_rejected(
    api: TestClient, make_token: MakeToken, claims: dict[str, object]
) -> None:
    token = make_token(uuid4(), **claims)

    assert api.get("/user", headers=bearer(token)).status_code == 401


@pytest.mark.parametrize("claim", ["sub", "exp", "iss", "aud"])
def test_token_missing_a_required_claim_is_rejected(
    api: TestClient, make_token: MakeToken, claim: str, signing_key: EllipticCurvePrivateKey
) -> None:
    payload = jwt.decode(make_token(uuid4()), options={"verify_signature": False})
    del payload[claim]
    token = jwt.encode(payload, signing_key, algorithm="ES256")

    assert api.get("/user", headers=bearer(token)).status_code == 401


def test_keys_unavailable_is_not_a_session_error(
    sample_app: FastAPI, make_token: MakeToken
) -> None:
    class DownJwksClient:
        def get_signing_key_from_jwt(self, token: str) -> None:
            raise PyJWKClientConnectionError("down")

    sample_app.dependency_overrides[get_token_verifier] = lambda: TokenVerifier(
        issuer=ISSUER, jwks_client=DownJwksClient()
    )

    response = TestClient(sample_app).get("/user", headers=bearer(make_token(uuid4())))

    assert response.status_code == 503
    assert response.json()["code"] == "auth_unavailable"


def test_session_is_scoped_to_the_token_owner(
    api: TestClient, make_token: MakeToken, two_owners: tuple[UUID, UUID]
) -> None:
    ana, beto = two_owners

    as_ana = api.get("/names", headers=bearer(make_token(ana))).json()
    as_beto = api.get("/names", headers=bearer(make_token(beto))).json()

    assert as_ana == {"owner_id": str(ana), "names": ["Ana"]}
    assert as_beto == {"owner_id": str(beto), "names": ["Beto"]}


def test_session_is_not_opened_without_a_token(api: TestClient) -> None:
    assert api.get("/names").status_code == 401


def test_session_commits_when_the_request_succeeds(
    api: TestClient, make_token: MakeToken, admin_engine: Engine, two_owners: tuple[UUID, UUID]
) -> None:
    ana, beto = two_owners

    response = api.post("/rename", headers=bearer(make_token(ana)))

    assert response.status_code == 200
    assert name_of(admin_engine, ana) == "Renombrada"
    assert name_of(admin_engine, beto) == "Beto"


def test_session_rolls_back_when_the_request_fails(
    api: TestClient, make_token: MakeToken, admin_engine: Engine, two_owners: tuple[UUID, UUID]
) -> None:
    ana, _ = two_owners

    response = api.post("/rename", params={"fail": True}, headers=bearer(make_token(ana)))

    assert response.status_code == 400
    assert name_of(admin_engine, ana) == "Ana"
