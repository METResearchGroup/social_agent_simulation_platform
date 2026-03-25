"""Security headers middleware for API responses.

Sets X-Content-Type-Options, X-Frame-Options, and optionally
Strict-Transport-Security to mitigate XSS, clickjacking, and MIME sniffing.
"""

import os


def _hsts_enabled() -> bool:
    """Return True if ENABLE_HSTS is set and truthy."""
    val = os.environ.get("ENABLE_HSTS", "").lower()
    return val in ("1", "true", "yes")
