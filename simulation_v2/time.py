"""Timestamp utilities for simulation_v2."""

from __future__ import annotations

from datetime import datetime, timezone

CREATED_AT_FORMAT: str = "%Y_%m_%d-%H:%M:%S"


def get_current_timestamp() -> str:
    """Return the current UTC timestamp in the contract format."""
    return datetime.now(timezone.utc).strftime(CREATED_AT_FORMAT)


__all__ = ["CREATED_AT_FORMAT", "get_current_timestamp"]
