"""Supabase JWT authentication dependency for protected routes."""

import os

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWTError

ENV_SUPABASE_JWT_SECRET: str = "SUPABASE_JWT_SECRET"
ENV_DISABLE_AUTH: str = "DISABLE_AUTH"
JWT_AUDIENCE: str = "authenticated"
JWT_ALGORITHMS: list[str] = ["HS256"]

# Mock payload when DISABLE_AUTH is set (local dev only)
_DEV_MOCK_PAYLOAD: dict = {"sub": "dev-user-id", "email": "dev@local"}


def _is_auth_disabled() -> bool:
    """True when DISABLE_AUTH=1 or DISABLE_AUTH=true (local dev bypass)."""
    val = os.environ.get(ENV_DISABLE_AUTH, "").strip().lower()
    return val in ("1", "true", "yes")


def _get_jwt_secret() -> str:
    """Read JWT secret from environment. Raises if not set."""
    secret = os.environ.get(ENV_SUPABASE_JWT_SECRET)
    if not secret or not secret.strip():
        raise RuntimeError(
            f"{ENV_SUPABASE_JWT_SECRET} must be set for protected routes. "
            "Obtain from Supabase Project Settings → API → JWT Secret."
        )
    return secret.strip()


class UnauthorizedError(Exception):
    """Raised when authentication fails. Use standard API error shape in handler."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        HTTPBearer(auto_error=False, description="Bearer token required")
    ),
) -> dict:
    """Verify Supabase JWT and return decoded claims. Raises UnauthorizedError on failure.

    Expects Authorization: Bearer <access_token>. Validates against SUPABASE_JWT_SECRET
    with audience="authenticated" and algorithm HS256.

    When DISABLE_AUTH=1 or DISABLE_AUTH=true, skips verification and returns a mock
    payload. Use only for local development.
    """
    if _is_auth_disabled():
        return _DEV_MOCK_PAYLOAD
    if credentials is None:
        raise UnauthorizedError("Missing or invalid Authorization header")
    token = credentials.credentials
    if not token or not token.strip():
        raise UnauthorizedError("Missing or invalid Authorization header")
    secret = _get_jwt_secret()
    try:
        payload = jwt.decode(
            token,
            secret,
            audience=JWT_AUDIENCE,
            algorithms=JWT_ALGORITHMS,
        )
    except PyJWTError:
        raise UnauthorizedError("Invalid or expired token") from None
    return payload
