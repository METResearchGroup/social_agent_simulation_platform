"""SQLite implementation of agent seed comment database adapter."""

from __future__ import annotations

from collections.abc import Iterable

from db.adapters.base import AgentSeedCommentDatabaseAdapter
from simulation.core.models.agent_seed_actions import AgentSeedComment

from ._validation import _require_sqlite_connection


def _placeholders(n: int) -> str:
    return ", ".join(["?"] * n)


class SQLiteAgentSeedCommentAdapter(AgentSeedCommentDatabaseAdapter):
    """SQLite implementation for agent-scoped seed comments."""

    def write_agent_seed_comments(
        self,
        seed_comments: Iterable[AgentSeedComment],
        *,
        conn: object,
    ) -> None:
        conn = _require_sqlite_connection(conn)
        for item in seed_comments:
            conn.execute(
                """
                INSERT INTO agent_seed_comments (
                    seed_comment_id, agent_handle, post_uri, text, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    item.seed_comment_id,
                    item.agent_handle,
                    item.post_uri,
                    item.text,
                    item.created_at,
                ),
            )

    def read_agent_seed_comments_by_agent_handles(
        self, agent_handles: Iterable[str], *, conn: object
    ) -> list[AgentSeedComment]:
        conn = _require_sqlite_connection(conn)
        handles = list(agent_handles)
        if not handles:
            return []
        rows = conn.execute(
            f"""
            SELECT seed_comment_id, agent_handle, post_uri, text, created_at
            FROM agent_seed_comments
            WHERE agent_handle IN ({_placeholders(len(handles))})
            ORDER BY agent_handle, post_uri, seed_comment_id
            """,
            tuple(handles),
        ).fetchall()
        return [
            AgentSeedComment(
                seed_comment_id=row[0],
                agent_handle=row[1],
                post_uri=row[2],
                text=row[3],
                created_at=row[4],
            )
            for row in rows
        ]
