"""SQLite implementation of comment action database adapter."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable

from db.adapters.base import CommentDatabaseAdapter
from simulation.core.models.generated.comment import GeneratedComment
from simulation.core.models.persisted_actions import PersistedComment

from ._serialization import _metadata_to_json


class SQLiteCommentAdapter(CommentDatabaseAdapter):
    """SQLite implementation for persisted comment actions."""

    def write_comments(
        self,
        run_id: str,
        turn_number: int,
        comments: Iterable[GeneratedComment],
        *,
        conn: object,
    ) -> None:
        """Insert comment rows for the given run and turn."""
        if not isinstance(conn, sqlite3.Connection):
            raise TypeError("SQLite adapter requires sqlite3.Connection")
        for g in comments:
            meta = g.metadata
            gen_meta_json = _metadata_to_json(meta) if meta else None
            model_used = getattr(meta, "model_used", None) if meta else None
            gen_created_at = getattr(meta, "created_at", None) if meta else None
            conn.execute(
                """
                INSERT INTO comments (
                    comment_id, run_id, turn_number, agent_handle, post_id, text,
                    created_at, explanation, model_used, generation_metadata_json,
                    generation_created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    g.comment.comment_id,
                    run_id,
                    turn_number,
                    g.comment.agent_id,
                    g.comment.post_id,
                    g.comment.text,
                    g.comment.created_at,
                    g.explanation or None,
                    model_used,
                    gen_meta_json,
                    gen_created_at,
                ),
            )

    def read_comments_by_run_turn(
        self, run_id: str, turn_number: int, *, conn: object
    ) -> list[PersistedComment]:
        """Read all comment rows for (run_id, turn_number). Ordered by agent_handle, post_id."""
        if not isinstance(conn, sqlite3.Connection):
            raise TypeError("SQLite adapter requires sqlite3.Connection")
        rows = conn.execute(
            """
            SELECT comment_id, run_id, turn_number, agent_handle, post_id, text,
                   created_at, explanation, model_used, generation_metadata_json,
                   generation_created_at
            FROM comments
            WHERE run_id = ? AND turn_number = ?
            ORDER BY agent_handle, post_id, comment_id
            """,
            (run_id, turn_number),
        ).fetchall()
        return [
            PersistedComment(
                comment_id=row[0],
                run_id=row[1],
                turn_number=row[2],
                agent_handle=row[3],
                post_id=row[4],
                text=row[5],
                created_at=row[6],
                explanation=row[7],
                model_used=row[8],
                generation_metadata_json=row[9],
                generation_created_at=row[10],
            )
            for row in rows
        ]
