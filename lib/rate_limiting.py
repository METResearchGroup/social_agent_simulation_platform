"""Rate limiting for FastAPI routes.

Uses slowapi. Import limiter in routes and app setup to avoid circular imports.
"""

from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

FALLBACK_CLIENT_IP: str = "127.0.0.1"


def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    """Return 429 with standard error shape matching other API errors."""
    return JSONResponse(
        status_code=HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": {
                "code": "RATE_LIMITED",
                "message": "Rate limit exceeded",
                "detail": None,
            }
        },
    )


def _get_rate_limit_key(request: Request) -> str:
    """Derive the client identifier used to group requests for rate limiting.

    Returns the effective client IP so requests from the same client share the same
    rate-limit bucket. Uses X-Forwarded-For when present (e.g. behind Railway proxy),
    otherwise request.client.host, or FALLBACK_CLIENT_IP when neither is available.
    """
    forwarded = request.headers.get("x-forwarded-for") or request.headers.get(
        "X-Forwarded-For"
    )
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return FALLBACK_CLIENT_IP


limiter = Limiter(key_func=_get_rate_limit_key)
