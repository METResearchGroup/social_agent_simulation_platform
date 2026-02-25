"""SQLite implementation of follow action database adapter."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable

from db.adapters.base import FollowDatabaseAdapter
from simulation.core.models.generated.follow import GeneratedFollow
from simulation.core.models.persisted_actions import PersistedFollow

from ._serialization import _metadata_to_json


class SQLiteFollowAdapter(FollowDatabaseAdapter):
    """SQLite implementation for persisted follow actions."""

    def write_follows(
        self,
        run_id: str,
        turn_number: int,
        follows: Iterable[GeneratedFollow],
        *,
        conn: object,
    ) -> None:
        """Insert follow rows for the given run and turn."""
        if not isinstance(conn, sqlite3.Connection):
            raise TypeError("SQLite adapter requires sqlite3.Connection")
        for g in follows:
            meta = g.metadata
            gen_meta_json = _metadata_to_json(meta) if meta else None
            model_used = getattr(meta, "model_used", None) if meta else None
            gen_created_at = getattr(meta, "created_at", None) if meta else None
            conn.execute(
                """
                INSERT INTO follows (
                    follow_id, run_id, turn_number, agent_handle, user_id,
                    created_at, explanation, model_used, generation_metadata_json,
                    generation_created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    g.follow.follow_id,
                    run_id,
                    turn_number,
                    g.follow.agent_id,
                    g.follow.user_id,
                    g.follow.created_at,
                    g.explanation or None,
                    model_used,
                    gen_meta_json,
                    gen_created_at,
                ),
            )

    def read_follows_by_run_turn(
        self, run_id: str, turn_number: int, *, conn: object
    ) -> list[PersistedFollow]:
        """Read all follow rows for (run_id, turn_number). Ordered by agent_handle, user_id."""
        if not isinstance(conn, sqlite3.Connection):
            raise TypeError("SQLite adapter requires sqlite3.Connection")
        rows = conn.execute(
            """
            SELECT follow_id, run_id, turn_number, agent_handle, user_id, created_at,
                   explanation, model_used, generation_metadata_json, generation_created_at
            FROM follows
            WHERE run_id = ? AND turn_number = ?
            ORDER BY agent_handle, user_id, follow_id
            """,
            (run_id, turn_number),
        ).fetchall()
        return [
            PersistedFollow(
                follow_id=row[0],
                run_id=row[1],
                turn_number=row[2],
                agent_handle=row[3],
                user_id=row[4],
                created_at=row[5],
                explanation=row[6],
                model_used=row[7],
                generation_metadata_json=row[8],
                generation_created_at=row[9],
            )
            for row in rows
        ]
