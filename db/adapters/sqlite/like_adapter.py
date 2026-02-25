"""SQLite implementation of like action database adapter."""

from __future__ import annotations

from collections.abc import Iterable

from db.adapters.base import LikeDatabaseAdapter
from simulation.core.models.generated.like import GeneratedLike
from simulation.core.models.persisted_actions import PersistedLike

from ._serialization import _metadata_to_json
from ._validation import _require_sqlite_connection


class SQLiteLikeAdapter(LikeDatabaseAdapter):
    """SQLite implementation for persisted like actions."""

    def write_likes(
        self,
        run_id: str,
        turn_number: int,
        likes: Iterable[GeneratedLike],
        *,
        conn: object,
    ) -> None:
        """Insert like rows for the given run and turn."""
        conn = _require_sqlite_connection(conn)
        for g in likes:
            meta = g.metadata
            gen_meta_json = _metadata_to_json(meta) if meta else None
            model_used = getattr(meta, "model_used", None) if meta else None
            gen_created_at = getattr(meta, "created_at", None) if meta else None
            conn.execute(
                """
                INSERT INTO likes (
                    like_id, run_id, turn_number, agent_handle, post_id,
                    created_at, explanation, model_used, generation_metadata_json,
                    generation_created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    g.like.like_id,
                    run_id,
                    turn_number,
                    g.like.agent_id,
                    g.like.post_id,
                    g.like.created_at,
                    g.explanation or None,
                    model_used,
                    gen_meta_json,
                    gen_created_at,
                ),
            )

    def read_likes_by_run_turn(
        self, run_id: str, turn_number: int, *, conn: object
    ) -> list[PersistedLike]:
        """Read all like rows for (run_id, turn_number). Ordered by agent_handle, post_id."""
        conn = _require_sqlite_connection(conn)
        rows = conn.execute(
            """
            SELECT like_id, run_id, turn_number, agent_handle, post_id, created_at,
                   explanation, model_used, generation_metadata_json, generation_created_at
            FROM likes
            WHERE run_id = ? AND turn_number = ?
            ORDER BY agent_handle, post_id, like_id
            """,
            (run_id, turn_number),
        ).fetchall()
        return [
            PersistedLike(
                like_id=row[0],
                run_id=row[1],
                turn_number=row[2],
                agent_handle=row[3],
                post_id=row[4],
                created_at=row[5],
                explanation=row[6],
                model_used=row[7],
                generation_metadata_json=row[8],
                generation_created_at=row[9],
            )
            for row in rows
        ]
