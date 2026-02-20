"""Supabase JWT authentication dependency for protected routes."""

import os

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWTError

ENV_SUPABASE_JWT_SECRET: str = "SUPABASE_JWT_SECRET"
JWT_AUDIENCE: str = "authenticated"
JWT_ALGORITHMS: list[str] = ["HS256"]


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
    """
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
