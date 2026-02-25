"""Shared serialization helpers for SQLite adapters."""

from __future__ import annotations

import json


def _metadata_to_json(metadata: object) -> str | None:
    """Serialize generation_metadata dict to JSON string. Returns None if missing or empty."""
    if metadata is None:
        return None
    if hasattr(metadata, "generation_metadata") and getattr(
        metadata, "generation_metadata"
    ):
        return json.dumps(getattr(metadata, "generation_metadata"))
    return None
