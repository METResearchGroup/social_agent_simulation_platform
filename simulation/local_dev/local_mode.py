"""Local development mode helpers.

Local mode is enabled when LOCAL=true (or 1/yes). It is intended for developer
workflows only and must be disallowed in production environments.
"""

from __future__ import annotations

from lib.env_utils import is_local_mode, is_production_env


def disallow_local_mode_in_production() -> None:
    """Fail fast if LOCAL is enabled in production-like environments."""
    if is_local_mode() and is_production_env():
        raise RuntimeError(
            "LOCAL must not be enabled in production. "
            "Local mode is for developer workflows only."
        )
