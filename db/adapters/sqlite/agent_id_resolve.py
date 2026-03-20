"""Resolve Bluesky-style handles to canonical agent_id rows (SQLite)."""

from __future__ import annotations

import sqlite3

from lib.agent_id import is_canonical_agent_id


def _norm_handle(value: str) -> str:
    t = (value or "").strip()
    if t.startswith("@"):
        t = t[1:]
    return t.strip().lower()


def resolve_agent_id_sqlite(conn: sqlite3.Connection, raw: str) -> str:
    """Return ``raw`` if already canonical; else resolve via ``agent.handle``."""
    if is_canonical_agent_id(raw):
        return raw
    want = _norm_handle(raw)
    rows = conn.execute("SELECT agent_id, handle FROM agent").fetchall()
    for agent_id, handle in rows:
        if _norm_handle(handle) == want:
            return str(agent_id)
    raise ValueError(f"Cannot resolve agent_id for {raw!r}")
