"""Canonical agent_id generation and validation helpers."""

from __future__ import annotations

import hashlib
import re
import secrets

CANONICAL_AGENT_ID_PATTERN = re.compile(r"^[0-9a-f]{16}$")


def canonical_agent_id(source: str | None = None) -> str:
    """Return a canonical 16-char lowercase hex agent ID.

    If source is provided, output is deterministic from stripped input.
    If source is omitted, entropy is used to produce a new canonical ID.
    """
    normalized = secrets.token_hex(32) if source is None else source.strip()
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return digest[:16]


def is_canonical_agent_id(value: str) -> bool:
    """Return True when value matches the canonical agent_id contract."""
    if not isinstance(value, str):
        return False
    return CANONICAL_AGENT_ID_PATTERN.fullmatch(value) is not None
