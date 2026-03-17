"""SQLite implementation of editable seed-state follow edge persistence."""

import sqlite3
from collections.abc import Iterable

from db.adapters.base import AgentFollowEdgeDatabaseAdapter
from lib.validation_decorators import validate_inputs
from simulation.core.models.agent_follow_edge import (
    AgentFollowEdge,
    AgentFollowEdgePage,
    AgentFollowEdgeWithTargetHandle,
)
from simulation.core.utils.validators import validate_agent_id

_LIST_EDGES_BY_FOLLOWER_SQL = """
SELECT
    agent_follow_edge_id,
    follower_agent_id,
    target_agent_id,
    created_at
FROM agent_follow_edges
WHERE follower_agent_id = ?
ORDER BY target_agent_id ASC, agent_follow_edge_id ASC
LIMIT ? OFFSET ?
"""
_COUNT_EDGES_BY_FOLLOWER_SQL = """
SELECT COUNT(*)
FROM agent_follow_edges
WHERE follower_agent_id = ?
"""
_COUNT_EDGES_BY_TARGET_SQL = """
SELECT COUNT(*)
FROM agent_follow_edges
WHERE target_agent_id = ?
"""
_LIST_EDGES_WITH_TARGETS_BY_FOLLOWER_SQL = """
SELECT
    edge.agent_follow_edge_id,
    edge.follower_agent_id,
    edge.target_agent_id,
    agent.handle AS target_handle,
    edge.created_at
FROM agent_follow_edges AS edge
INNER JOIN agent ON agent.agent_id = edge.target_agent_id
WHERE edge.follower_agent_id = ?
ORDER BY edge.target_agent_id ASC, edge.agent_follow_edge_id ASC
LIMIT ? OFFSET ?
"""
_LIST_EDGES_FOR_FOLLOWER_AGENT_IDS_ORDER_BY = (
    "ORDER BY follower_agent_id ASC, target_agent_id ASC, agent_follow_edge_id ASC"
)
_DELETE_EDGE_SQL = """
DELETE FROM agent_follow_edges
WHERE follower_agent_id = ? AND target_agent_id = ?
"""
_LIST_CONNECTED_AGENT_IDS_SQL = """
SELECT connected_agent_id
FROM (
    SELECT target_agent_id AS connected_agent_id
    FROM agent_follow_edges
    WHERE follower_agent_id = ?
    UNION
    SELECT follower_agent_id AS connected_agent_id
    FROM agent_follow_edges
    WHERE target_agent_id = ?
)
ORDER BY connected_agent_id ASC
"""
_DELETE_EDGES_FOR_AGENT_SQL = """
DELETE FROM agent_follow_edges
WHERE follower_agent_id = ? OR target_agent_id = ?
"""


class SQLiteAgentFollowEdgeAdapter(AgentFollowEdgeDatabaseAdapter):
    """SQLite implementation of AgentFollowEdgeDatabaseAdapter."""

    def _row_to_edge(self, row: sqlite3.Row) -> AgentFollowEdge:
        return AgentFollowEdge(
            agent_follow_edge_id=row["agent_follow_edge_id"],
            follower_agent_id=row["follower_agent_id"],
            target_agent_id=row["target_agent_id"],
            created_at=row["created_at"],
        )

    def _row_to_edge_with_target_handle(
        self, row: sqlite3.Row
    ) -> AgentFollowEdgeWithTargetHandle:
        return AgentFollowEdgeWithTargetHandle(
            agent_follow_edge_id=row["agent_follow_edge_id"],
            follower_agent_id=row["follower_agent_id"],
            target_agent_id=row["target_agent_id"],
            target_handle=row["target_handle"],
            created_at=row["created_at"],
        )

    def write_agent_follow_edge(
        self, edge: AgentFollowEdge, *, conn: sqlite3.Connection
    ) -> None:
        """Insert a follow edge row."""
        conn.execute(
            (
                "INSERT INTO agent_follow_edges "
                "(agent_follow_edge_id, follower_agent_id, target_agent_id, created_at) "
                "VALUES (?, ?, ?, ?)"
            ),
            (
                edge.agent_follow_edge_id,
                edge.follower_agent_id,
                edge.target_agent_id,
                edge.created_at,
            ),
        )

    @validate_inputs((validate_agent_id, "follower_agent_id"))
    def read_edges_by_follower_agent_id(
        self,
        follower_agent_id: str,
        *,
        limit: int,
        offset: int,
        conn: sqlite3.Connection,
    ) -> list[AgentFollowEdge]:
        """Read follow edges for a follower in deterministic order."""
        rows = conn.execute(
            _LIST_EDGES_BY_FOLLOWER_SQL,
            (follower_agent_id, limit, offset),
        ).fetchall()
        return [self._row_to_edge(row) for row in rows]

    @validate_inputs((validate_agent_id, "follower_agent_id"))
    def count_edges_by_follower_agent_id(
        self, follower_agent_id: str, *, conn: sqlite3.Connection
    ) -> int:
        """Count outgoing follow edges for a follower agent."""
        row = conn.execute(
            _COUNT_EDGES_BY_FOLLOWER_SQL, (follower_agent_id,)
        ).fetchone()
        return int(row[0]) if row is not None else 0

    @validate_inputs((validate_agent_id, "target_agent_id"))
    def count_edges_by_target_agent_id(
        self, target_agent_id: str, *, conn: sqlite3.Connection
    ) -> int:
        """Count incoming follow edges for a target agent."""
        row = conn.execute(_COUNT_EDGES_BY_TARGET_SQL, (target_agent_id,)).fetchone()
        return int(row[0]) if row is not None else 0

    @validate_inputs((validate_agent_id, "follower_agent_id"))
    def read_edge_page_by_follower_agent_id(
        self,
        follower_agent_id: str,
        *,
        limit: int,
        offset: int,
        conn: sqlite3.Connection,
    ) -> AgentFollowEdgePage:
        """Read a consistent page of follow edges with resolved target handles."""
        total_row = conn.execute(
            _COUNT_EDGES_BY_FOLLOWER_SQL,
            (follower_agent_id,),
        ).fetchone()
        rows = conn.execute(
            _LIST_EDGES_WITH_TARGETS_BY_FOLLOWER_SQL,
            (follower_agent_id, limit, offset),
        ).fetchall()
        return AgentFollowEdgePage(
            total=int(total_row[0]) if total_row is not None else 0,
            items=[self._row_to_edge_with_target_handle(row) for row in rows],
        )

    def read_edges_for_follower_agent_ids(
        self,
        follower_agent_ids: Iterable[str],
        *,
        conn: sqlite3.Connection,
    ) -> list[AgentFollowEdge]:
        """Read follow edges for multiple followers in deterministic order."""
        follower_agent_id_list = [
            validate_agent_id(follower_agent_id)
            for follower_agent_id in follower_agent_ids
        ]
        if not follower_agent_id_list:
            return []

        placeholders = ", ".join("?" for _ in follower_agent_id_list)
        sql = (
            "SELECT agent_follow_edge_id, follower_agent_id, target_agent_id, created_at "
            "FROM agent_follow_edges "
            f"WHERE follower_agent_id IN ({placeholders}) "
            f"{_LIST_EDGES_FOR_FOLLOWER_AGENT_IDS_ORDER_BY}"
        )
        rows = conn.execute(sql, tuple(follower_agent_id_list)).fetchall()
        return [self._row_to_edge(row) for row in rows]

    @validate_inputs(
        (validate_agent_id, "follower_agent_id"),
        (validate_agent_id, "target_agent_id"),
    )
    def delete_edge(
        self,
        follower_agent_id: str,
        target_agent_id: str,
        *,
        conn: sqlite3.Connection,
    ) -> bool:
        """Delete one follow edge row."""
        cursor = conn.execute(_DELETE_EDGE_SQL, (follower_agent_id, target_agent_id))
        return cursor.rowcount > 0

    @validate_inputs((validate_agent_id, "agent_id"))
    def read_connected_agent_ids(
        self, agent_id: str, *, conn: sqlite3.Connection
    ) -> list[str]:
        """Read all distinct agent_ids connected to the given agent."""
        rows = conn.execute(
            _LIST_CONNECTED_AGENT_IDS_SQL, (agent_id, agent_id)
        ).fetchall()
        return [str(row["connected_agent_id"]) for row in rows]

    @validate_inputs((validate_agent_id, "agent_id"))
    def delete_edges_for_agent(
        self, agent_id: str, *, conn: sqlite3.Connection
    ) -> None:
        """Delete every follow edge where the given agent participates."""
        conn.execute(_DELETE_EDGES_FOR_AGENT_SQL, (agent_id, agent_id))
