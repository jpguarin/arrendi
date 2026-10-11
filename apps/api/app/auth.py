from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientConnectionError, PyJWKClientError

# Supabase signs with asymmetric keys. Never accept HS256: the public key is public.
ALGORITHMS = ["ES256", "RS256"]
AUDIENCE = "authenticated"
JWKS_CACHE_SECONDS = 600


class InvalidTokenError(Exception):
    """The token is missing something, expired, or not signed by our Supabase project."""


class AuthUnavailableError(Exception):
    """Supabase's public keys could not be fetched, so no token can be checked."""


@dataclass(frozen=True)
class AuthUser:
    owner_id: UUID
    email: str | None
    name: str | None


class JwksClient(Protocol):
    def get_signing_key_from_jwt(self, token: str) -> Any: ...


class TokenVerifier:
    def __init__(self, issuer: str, jwks_client: JwksClient) -> None:
        self.issuer = issuer
        self.jwks_client = jwks_client

    @classmethod
    def for_supabase(cls, supabase_url: str) -> "TokenVerifier":
        issuer = f"{supabase_url.rstrip('/')}/auth/v1"
        jwks_client = PyJWKClient(
            f"{issuer}/.well-known/jwks.json", cache_keys=True, lifespan=JWKS_CACHE_SECONDS
        )
        return cls(issuer=issuer, jwks_client=jwks_client)

    def verify(self, token: str) -> AuthUser:
        try:
            key = self.jwks_client.get_signing_key_from_jwt(token).key
        except PyJWKClientConnectionError as error:
            raise AuthUnavailableError from error
        except (PyJWKClientError, jwt.InvalidTokenError) as error:
            raise InvalidTokenError from error

        try:
            claims = jwt.decode(
                token,
                key,
                algorithms=ALGORITHMS,
                issuer=self.issuer,
                audience=AUDIENCE,
                options={"require": ["sub", "exp", "iss", "aud"]},
            )
            owner_id = UUID(claims["sub"])
        except (jwt.InvalidTokenError, ValueError) as error:
            raise InvalidTokenError from error

        if claims.get("is_anonymous"):
            raise InvalidTokenError

        metadata = claims.get("user_metadata") or {}
        return AuthUser(
            owner_id=owner_id,
            email=claims.get("email") or None,
            name=metadata.get("full_name") or metadata.get("name") or None,
        )
