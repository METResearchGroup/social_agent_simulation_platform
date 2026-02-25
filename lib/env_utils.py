"""Environment flag helpers.

Centralizes common environment parsing used by local-dev mode and safety guards.
"""

from __future__ import annotations

import os

TRUTHY_ENV_VALUES: frozenset[str] = frozenset({"1", "true", "yes"})


def parse_bool_env(name: str) -> bool:
    """Return True if env var is set to a truthy value.

    Truthy values are: 1, true, yes (case-insensitive, surrounding whitespace ignored).
    Missing or any other value returns False.
    """
    val = os.environ.get(name, "")
    return val.strip().lower() in TRUTHY_ENV_VALUES


def is_local_mode() -> bool:
    """True when LOCAL is enabled."""
    return parse_bool_env("LOCAL")


def is_production_env() -> bool:
    """True when environment indicates production.

    Conservative / fail-safe:
    - ENV or ENVIRONMENT equal "production" or "prod" => production
    - any non-empty RAILWAY_ENVIRONMENT => production
    """
    env = os.environ.get("ENV", "").strip().lower()
    environment = os.environ.get("ENVIRONMENT", "").strip().lower()
    railway = os.environ.get("RAILWAY_ENVIRONMENT", "").strip()
    return (
        env in ("production", "prod")
        or environment in ("production", "prod")
        or bool(railway)
    )
