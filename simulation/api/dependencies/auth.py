"""Supabase JWT authentication dependency for protected routes."""

import functools
import os

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient, PyJWTError

from lib.env_utils import is_local_mode, is_production_env, parse_bool_env

ENV_SUPABASE_JWT_SECRET: str = "SUPABASE_JWT_SECRET"
ENV_SUPABASE_URL: str = "SUPABASE_URL"
ENV_DISABLE_AUTH: str = "DISABLE_AUTH"
JWT_AUDIENCE: str = "authenticated"
JWT_ALGORITHMS_HS256: list[str] = ["HS256"]

# Mock payload when DISABLE_AUTH is set (local dev only)
_DEV_MOCK_PAYLOAD: dict = {"sub": "dev-user-id", "email": "dev@local"}


def _is_auth_disabled() -> bool:
    """True when auth bypass is enabled (local dev only)."""
    return parse_bool_env(ENV_DISABLE_AUTH) or is_local_mode()


def disallow_auth_bypass_in_production() -> None:
    """Raise at startup if DISABLE_AUTH is set in production. Call from lifespan."""
    if _is_auth_disabled() and is_production_env():
        raise RuntimeError(
            f"{ENV_DISABLE_AUTH} must not be set in production. "
            "Auth bypass is for local development only. "
            "(Note: LOCAL=true also enables auth bypass.)"
        )


def _get_jwt_secret() -> str:
    """Read JWT secret from environment. Raises if not set."""
    secret = os.environ.get(ENV_SUPABASE_JWT_SECRET)
    if not secret or not secret.strip():
        raise RuntimeError(
            f"{ENV_SUPABASE_JWT_SECRET} must be set for protected routes. "
            "Obtain from Supabase Project Settings → API → JWT Secret."
        )
    return secret.strip()


def _get_supabase_url() -> str | None:
    """Project URL, e.g. https://<ref>.supabase.co — used for JWKS when tokens are not HS256."""
    raw = os.environ.get(ENV_SUPABASE_URL)
    if not raw or not raw.strip():
        return None
    return raw.strip().rstrip("/")


@functools.lru_cache(maxsize=4)
def _jwks_client_for(jwks_url: str) -> PyJWKClient:
    return PyJWKClient(jwks_url)


class UnauthorizedError(Exception):
    """Raised when authentication fails. Use standard API error shape in handler."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def _decode_supabase_access_token(token: str) -> dict:
    """Verify Supabase user JWT: HS256 via shared secret, or asymmetric via JWKS."""
    header = jwt.get_unverified_header(token)
    alg = header.get("alg") or "HS256"

    if alg == "HS256":
        secret = _get_jwt_secret()
        return jwt.decode(
            token,
            secret,
            audience=JWT_AUDIENCE,
            algorithms=JWT_ALGORITHMS_HS256,
        )

    supabase_url = _get_supabase_url()
    if not supabase_url:
        raise UnauthorizedError(
            "Access token is not HS256; set "
            f"{ENV_SUPABASE_URL} on the API (same value as the UI’s Supabase project URL, "
            "e.g. https://<project-ref>.supabase.co) so the API can verify it via JWKS."
        )

    jwks_url = f"{supabase_url}/auth/v1/.well-known/jwks.json"
    try:
        jwks_client = _jwks_client_for(jwks_url)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
    except Exception:
        raise UnauthorizedError("Invalid or expired token") from None

    try:
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=[alg],
            audience=JWT_AUDIENCE,
        )
    except PyJWTError:
        raise UnauthorizedError("Invalid or expired token") from None


def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        HTTPBearer(auto_error=False, description="Bearer token required")
    ),
) -> dict:
    """Verify Supabase JWT and return decoded claims. Raises UnauthorizedError on failure.

    Expects Authorization: Bearer <access_token>.

    - HS256 tokens: validated with ``SUPABASE_JWT_SECRET`` (legacy shared secret).
    - RS256 / other asymmetric tokens: validated using the project JWKS at
      ``{SUPABASE_URL}/auth/v1/.well-known/jwks.json`` (set ``SUPABASE_URL`` to the same
      project URL as the frontend, e.g. ``https://<ref>.supabase.co``).

    When DISABLE_AUTH=1 or DISABLE_AUTH=true (and not in production), skips verification
    and returns a mock payload. Use only for local development.
    """
    if _is_auth_disabled():
        if is_production_env():
            raise RuntimeError(
                f"{ENV_DISABLE_AUTH} must not be set in production. "
                "Auth bypass is for local development only. "
                "(Note: LOCAL=true also enables auth bypass.)"
            )
        return _DEV_MOCK_PAYLOAD.copy()
    if credentials is None:
        raise UnauthorizedError("Missing or invalid Authorization header")
    token = credentials.credentials
    if not token or not token.strip():
        raise UnauthorizedError("Missing or invalid Authorization header")
    try:
        return _decode_supabase_access_token(token.strip())
    except PyJWTError:
        raise UnauthorizedError("Invalid or expired token") from None
