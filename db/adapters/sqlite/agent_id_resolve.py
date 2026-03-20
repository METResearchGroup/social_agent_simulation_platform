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
    """Resolve to canonical agent_id. Handles: validate via agent table; else resolve via agent.handle."""
    want = _norm_handle(raw) if not is_canonical_agent_id(raw) else None
    if want is None:
        row = conn.execute(
            "SELECT agent_id FROM agent WHERE agent_id = ? LIMIT 1", (raw.strip(),)
        ).fetchone()
        if row is not None:
            return str(row[0])
        raise ValueError(f"Cannot resolve agent_id for {raw!r} (not in agent table)")
    row = conn.execute(
        "SELECT agent_id FROM agent WHERE lower(trim(ltrim(trim(coalesce(handle,'')), '@'))) = ? LIMIT 1",
        (want,),
    ).fetchone()
    if row is not None:
        return str(row[0])
    raise ValueError(f"Cannot resolve agent_id for {raw!r}")
