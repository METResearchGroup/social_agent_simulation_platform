"""SQLite implementation of agent seed follow database adapter."""

from __future__ import annotations

from collections.abc import Iterable

from db.adapters.base import AgentSeedFollowDatabaseAdapter
from simulation.core.models.agent_seed_actions import AgentSeedFollow

from ._validation import _require_sqlite_connection


def _placeholders(n: int) -> str:
    return ", ".join(["?"] * n)


class SQLiteAgentSeedFollowAdapter(AgentSeedFollowDatabaseAdapter):
    """SQLite implementation for agent-scoped seed follows."""

    def write_agent_seed_follows(
        self,
        seed_follows: Iterable[AgentSeedFollow],
        *,
        conn: object,
    ) -> None:
        conn = _require_sqlite_connection(conn)
        for item in seed_follows:
            conn.execute(
                """
                INSERT OR IGNORE INTO agent_seed_follows (
                    seed_follow_id, agent_handle, user_id, created_at
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    item.seed_follow_id,
                    item.agent_handle,
                    item.user_id,
                    item.created_at,
                ),
            )

    def read_agent_seed_follows_by_agent_handles(
        self, agent_handles: Iterable[str], *, conn: object
    ) -> list[AgentSeedFollow]:
        conn = _require_sqlite_connection(conn)
        handles = list(agent_handles)
        if not handles:
            return []
        rows = conn.execute(
            f"""
            SELECT seed_follow_id, agent_handle, user_id, created_at
            FROM agent_seed_follows
            WHERE agent_handle IN ({_placeholders(len(handles))})
            ORDER BY agent_handle, user_id, seed_follow_id
            """,
            tuple(handles),
        ).fetchall()
        return [
            AgentSeedFollow(
                seed_follow_id=row[0],
                agent_handle=row[1],
                user_id=row[2],
                created_at=row[3],
            )
            for row in rows
        ]
