"""SQLite implementation of agent seed like database adapter."""

from __future__ import annotations

from collections.abc import Iterable

from db.adapters.base import AgentSeedLikeDatabaseAdapter
from simulation.core.models.agent_seed_actions import AgentSeedLike

from ._validation import _require_sqlite_connection


def _placeholders(n: int) -> str:
    return ", ".join(["?"] * n)


class SQLiteAgentSeedLikeAdapter(AgentSeedLikeDatabaseAdapter):
    """SQLite implementation for agent-scoped seed likes."""

    def write_agent_seed_likes(
        self,
        seed_likes: Iterable[AgentSeedLike],
        *,
        conn: object,
    ) -> None:
        conn = _require_sqlite_connection(conn)
        for item in seed_likes:
            conn.execute(
                """
                INSERT OR IGNORE INTO agent_seed_likes (
                    seed_like_id, agent_handle, post_uri, created_at
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    item.seed_like_id,
                    item.agent_handle,
                    item.post_uri,
                    item.created_at,
                ),
            )

    def read_agent_seed_likes_by_agent_handles(
        self, agent_handles: Iterable[str], *, conn: object
    ) -> list[AgentSeedLike]:
        conn = _require_sqlite_connection(conn)
        handles = list(agent_handles)
        if not handles:
            return []
        rows = conn.execute(
            f"""
            SELECT seed_like_id, agent_handle, post_uri, created_at
            FROM agent_seed_likes
            WHERE agent_handle IN ({_placeholders(len(handles))})
            ORDER BY agent_handle, post_uri, seed_like_id
            """,
            tuple(handles),
        ).fetchall()
        return [
            AgentSeedLike(
                seed_like_id=row[0],
                agent_handle=row[1],
                post_uri=row[2],
                created_at=row[3],
            )
            for row in rows
        ]
