"""Helpers for the canonical ``turns`` parent row.

Some persistence paths insert a placeholder ``turns`` row so child rows in
``turn_generated_feeds`` (and related ``turn_*`` action tables) satisfy foreign
keys. ``SQLiteRunAdapter.write_turn_metadata`` replaces that stub or inserts the
final row as part of the per-turn write flow.
"""

from __future__ import annotations

import json
import sqlite3

from simulation.core.models.actions import TurnAction

# Matches ``lib.timestamp_utils.CREATED_AT_FORMAT`` shape; never used as a real timestamp.
TURN_PARENT_PLACEHOLDER_CREATED_AT = "1970_01_01-00:00:00"


def turn_parent_stub_total_actions_json() -> str:
    return json.dumps({k.value: 0 for k in TurnAction})


def ensure_turn_parent_stub_for_feed_write(
    conn: sqlite3.Connection, *, run_id: str, turn_number: int
) -> None:
    """Insert a placeholder ``turns`` row so ``turn_generated_feeds`` FK checks pass."""
    conn.execute(
        """
        INSERT OR IGNORE INTO turns (run_id, turn_number, total_actions, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            run_id,
            turn_number,
            turn_parent_stub_total_actions_json(),
            TURN_PARENT_PLACEHOLDER_CREATED_AT,
        ),
    )
