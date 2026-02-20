"""Security headers middleware for API responses.

Sets X-Content-Type-Options, X-Frame-Options, and optionally
Strict-Transport-Security to mitigate XSS, clickjacking, and MIME sniffing.
"""

import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


def _hsts_enabled() -> bool:
    """Return True if ENABLE_HSTS is set and truthy."""
    val = os.environ.get("ENABLE_HSTS", "").lower()
    return val in ("1", "true", "yes")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all API responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        if _hsts_enabled():
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response
