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
    if is_canonical_agent_id(raw):
        row = conn.execute(
            "SELECT agent_id FROM agent WHERE agent_id = ? LIMIT 1", (raw.strip(),)
        ).fetchone()
        if row is not None:
            return str(row[0])
        raise ValueError(f"Cannot resolve agent_id for {raw!r} (not in agent table)")

    want = _norm_handle(raw)
    rows = conn.execute(
        "SELECT agent_id, handle FROM agent WHERE handle IS NOT NULL AND handle != ''"
    ).fetchall()
    matches: list[tuple[str, str]] = []
    for agent_id, handle in rows:
        if _norm_handle(handle) == want:
            matches.append((str(agent_id), handle or ""))

    if len(matches) == 0:
        raise ValueError(f"Cannot resolve agent_id for {raw!r}")
    if len(matches) > 1:
        conflict_info = ", ".join(f"{aid!r} ({h!r})" for aid, h in matches)
        raise ValueError(
            f"Ambiguous handle {raw!r}: multiple agents match: {conflict_info}"
        )
    return matches[0][0]
