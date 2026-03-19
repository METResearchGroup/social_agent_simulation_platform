"""Shared serialization helpers for SQLite adapters."""

from __future__ import annotations

import json


def _metadata_to_json(metadata: object) -> str | None:
    """Serialize generation_metadata dict to JSON string. Returns None if missing or empty."""
    if metadata is None:
        return None
    generation_metadata = getattr(metadata, "generation_metadata", None)
    if generation_metadata:
        return json.dumps(generation_metadata)
    return None
