"""`TokenVerifier.for_supabase` against a local server that publishes keys like Supabase does."""

import json
import threading
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePrivateKey
from jwt.algorithms import ECAlgorithm

from app.auth import AuthUnavailableError, InvalidTokenError, TokenVerifier

KEY_ID = "key-1"


@pytest.fixture
def project_key() -> EllipticCurvePrivateKey:
    return ec.generate_private_key(ec.SECP256R1())


@pytest.fixture
def supabase_url(project_key: EllipticCurvePrivateKey) -> Iterator[str]:
    jwk = json.loads(ECAlgorithm.to_jwk(project_key.public_key())) | {"kid": KEY_ID, "alg": "ES256"}
    body = json.dumps({"keys": [jwk]}).encode()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            found = self.path == "/auth/v1/.well-known/jwks.json"
            self.send_response(200 if found else 404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body if found else b"{}")

        def log_message(self, *args: object) -> None:
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()


def sign(key: EllipticCurvePrivateKey, supabase_url: str, key_id: str = KEY_ID) -> str:
    payload = {
        "sub": str(uuid4()),
        "iss": f"{supabase_url}/auth/v1",
        "aud": "authenticated",
        "exp": datetime.now(UTC) + timedelta(hours=1),
        "email": "ana@example.com",
    }
    return jwt.encode(payload, key, algorithm="ES256", headers={"kid": key_id})


def test_token_is_verified_with_the_published_key(
    supabase_url: str, project_key: EllipticCurvePrivateKey
) -> None:
    verifier = TokenVerifier.for_supabase(supabase_url + "/")

    user = verifier.verify(sign(project_key, supabase_url))

    assert user.email == "ana@example.com"


def test_token_with_an_unpublished_key_id_is_rejected(
    supabase_url: str, project_key: EllipticCurvePrivateKey
) -> None:
    verifier = TokenVerifier.for_supabase(supabase_url)

    with pytest.raises(InvalidTokenError):
        verifier.verify(sign(project_key, supabase_url, key_id="unknown"))


def test_token_signed_with_another_key_is_rejected(supabase_url: str) -> None:
    verifier = TokenVerifier.for_supabase(supabase_url)

    with pytest.raises(InvalidTokenError):
        verifier.verify(sign(ec.generate_private_key(ec.SECP256R1()), supabase_url))


def test_unreachable_keys_are_reported_as_unavailable(
    project_key: EllipticCurvePrivateKey,
) -> None:
    unreachable = "http://127.0.0.1:1"
    verifier = TokenVerifier.for_supabase(unreachable)

    with pytest.raises(AuthUnavailableError):
        verifier.verify(sign(project_key, unreachable))
