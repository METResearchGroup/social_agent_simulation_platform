"""SQLite implementation of seed follow-edge database adapter."""

from __future__ import annotations

import sqlite3

from db.adapters.base import AgentFollowEdgeDatabaseAdapter
from db.adapters.sqlite.schema_utils import ordered_column_names, required_column_names
from db.adapters.sqlite.sqlite import validate_required_fields
from db.schema import agent_follow_edges
from lib.validation_decorators import validate_inputs
from simulation.core.models.agent_follow_edge import AgentFollowEdge
from simulation.core.utils.validators import validate_agent_id

from ._validation import _require_sqlite_connection

AGENT_FOLLOW_EDGE_COLUMNS = ordered_column_names(agent_follow_edges)
AGENT_FOLLOW_EDGE_REQUIRED_FIELDS = required_column_names(agent_follow_edges)
_INSERT_AGENT_FOLLOW_EDGE_SQL = (
    f"INSERT INTO agent_follow_edges ({', '.join(AGENT_FOLLOW_EDGE_COLUMNS)}) "
    f"VALUES ({', '.join('?' for _ in AGENT_FOLLOW_EDGE_COLUMNS)})"
)


class SQLiteAgentFollowEdgeAdapter(AgentFollowEdgeDatabaseAdapter):
    """SQLite implementation of AgentFollowEdgeDatabaseAdapter."""

    def _validate_agent_follow_edge_row(self, row: sqlite3.Row) -> None:
        validate_required_fields(row, AGENT_FOLLOW_EDGE_REQUIRED_FIELDS)

    def _row_to_agent_follow_edge(self, row: sqlite3.Row) -> AgentFollowEdge:
        return AgentFollowEdge(
            agent_follow_edge_id=row["agent_follow_edge_id"],
            follower_agent_id=row["follower_agent_id"],
            target_agent_id=row["target_agent_id"],
            created_at=row["created_at"],
        )

    def write_agent_follow_edge(self, edge: AgentFollowEdge, *, conn: object) -> None:
        """Insert one follow edge row."""
        sqlite_conn = _require_sqlite_connection(conn)
        row_values = tuple(getattr(edge, col) for col in AGENT_FOLLOW_EDGE_COLUMNS)
        sqlite_conn.execute(_INSERT_AGENT_FOLLOW_EDGE_SQL, row_values)

    @validate_inputs(
        (validate_agent_id, "follower_agent_id"),
        (validate_agent_id, "target_agent_id"),
    )
    def read_agent_follow_edge(
        self,
        follower_agent_id: str,
        target_agent_id: str,
        *,
        conn: object,
    ) -> AgentFollowEdge | None:
        """Read one follow edge by its natural key."""
        sqlite_conn = _require_sqlite_connection(conn)
        row = sqlite_conn.execute(
            """
            SELECT *
            FROM agent_follow_edges
            WHERE follower_agent_id = ? AND target_agent_id = ?
            """,
            (follower_agent_id, target_agent_id),
        ).fetchone()
        if row is None:
            return None
        self._validate_agent_follow_edge_row(row)
        return self._row_to_agent_follow_edge(row)

    @validate_inputs((validate_agent_id, "follower_agent_id"))
    def read_agent_follow_edges_by_follower_agent_id(
        self,
        follower_agent_id: str,
        *,
        limit: int,
        offset: int,
        conn: object,
    ) -> list[AgentFollowEdge]:
        """Read follow edges for one follower in deterministic order."""
        sqlite_conn = _require_sqlite_connection(conn)
        rows = sqlite_conn.execute(
            """
            SELECT *
            FROM agent_follow_edges
            WHERE follower_agent_id = ?
            ORDER BY target_agent_id ASC, agent_follow_edge_id ASC
            LIMIT ? OFFSET ?
            """,
            (follower_agent_id, limit, offset),
        ).fetchall()
        result: list[AgentFollowEdge] = []
        for row in rows:
            self._validate_agent_follow_edge_row(row)
            result.append(self._row_to_agent_follow_edge(row))
        return result

    @validate_inputs((validate_agent_id, "follower_agent_id"))
    def count_agent_follow_edges_by_follower_agent_id(
        self, follower_agent_id: str, *, conn: object
    ) -> int:
        """Count follow edges where the given agent is the follower."""
        sqlite_conn = _require_sqlite_connection(conn)
        row = sqlite_conn.execute(
            """
            SELECT COUNT(*)
            FROM agent_follow_edges
            WHERE follower_agent_id = ?
            """,
            (follower_agent_id,),
        ).fetchone()
        return int(row[0])

    @validate_inputs((validate_agent_id, "target_agent_id"))
    def count_agent_follow_edges_by_target_agent_id(
        self, target_agent_id: str, *, conn: object
    ) -> int:
        """Count follow edges where the given agent is the target."""
        sqlite_conn = _require_sqlite_connection(conn)
        row = sqlite_conn.execute(
            """
            SELECT COUNT(*)
            FROM agent_follow_edges
            WHERE target_agent_id = ?
            """,
            (target_agent_id,),
        ).fetchone()
        return int(row[0])

    @validate_inputs(
        (validate_agent_id, "follower_agent_id"),
        (validate_agent_id, "target_agent_id"),
    )
    def delete_agent_follow_edge(
        self,
        follower_agent_id: str,
        target_agent_id: str,
        *,
        conn: object,
    ) -> bool:
        """Delete one follow edge row by its natural key."""
        sqlite_conn = _require_sqlite_connection(conn)
        cursor = sqlite_conn.execute(
            """
            DELETE FROM agent_follow_edges
            WHERE follower_agent_id = ? AND target_agent_id = ?
            """,
            (follower_agent_id, target_agent_id),
        )
        return cursor.rowcount > 0
