"""SQLite implementation of seed follow-edge repository."""

from __future__ import annotations

import sqlite3

from db.adapters.base import AgentFollowEdgeDatabaseAdapter, TransactionProvider
from db.repositories.interfaces import AgentFollowEdgeRepository
from lib.validation_decorators import validate_inputs
from simulation.core.models.agent_follow_edge import AgentFollowEdge
from simulation.core.utils.validators import validate_agent_id


class DuplicateAgentFollowEdgeError(Exception):
    """Raised when a seed follow edge already exists for the same natural key."""


class SQLiteAgentFollowEdgeRepository(AgentFollowEdgeRepository):
    """SQLite implementation of AgentFollowEdgeRepository."""

    def __init__(
        self,
        *,
        db_adapter: AgentFollowEdgeDatabaseAdapter,
        transaction_provider: TransactionProvider,
    ):
        self._db_adapter = db_adapter
        self._transaction_provider = transaction_provider

    def create_agent_follow_edge(
        self,
        edge: AgentFollowEdge,
        conn: object | None = None,
    ) -> AgentFollowEdge:
        """Create one follow edge row."""
        try:
            if conn is not None:
                self._db_adapter.write_agent_follow_edge(edge, conn=conn)
            else:
                with self._transaction_provider.run_transaction() as c:
                    self._db_adapter.write_agent_follow_edge(edge, conn=c)
        except sqlite3.IntegrityError as exc:
            if _is_duplicate_agent_follow_edge_integrity_error(exc):
                raise DuplicateAgentFollowEdgeError(edge.follower_agent_id) from exc
            raise
        return edge

    @validate_inputs(
        (validate_agent_id, "follower_agent_id"),
        (validate_agent_id, "target_agent_id"),
    )
    def get_agent_follow_edge(
        self,
        follower_agent_id: str,
        target_agent_id: str,
        conn: object | None = None,
    ) -> AgentFollowEdge | None:
        """Get one follow edge by natural key."""
        if conn is not None:
            return self._db_adapter.read_agent_follow_edge(
                follower_agent_id,
                target_agent_id,
                conn=conn,
            )
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_agent_follow_edge(
                follower_agent_id,
                target_agent_id,
                conn=c,
            )

    @validate_inputs((validate_agent_id, "follower_agent_id"))
    def list_agent_follow_edges_by_follower_agent_id(
        self,
        follower_agent_id: str,
        *,
        limit: int,
        offset: int,
        conn: object | None = None,
    ) -> list[AgentFollowEdge]:
        """List follow edges for one follower in deterministic order."""
        if conn is not None:
            return self._db_adapter.read_agent_follow_edges_by_follower_agent_id(
                follower_agent_id,
                limit=limit,
                offset=offset,
                conn=conn,
            )
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_agent_follow_edges_by_follower_agent_id(
                follower_agent_id,
                limit=limit,
                offset=offset,
                conn=c,
            )

    @validate_inputs((validate_agent_id, "follower_agent_id"))
    def count_agent_follow_edges_by_follower_agent_id(
        self, follower_agent_id: str, conn: object | None = None
    ) -> int:
        """Count follow edges where the given agent is the follower."""
        if conn is not None:
            return self._db_adapter.count_agent_follow_edges_by_follower_agent_id(
                follower_agent_id,
                conn=conn,
            )
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.count_agent_follow_edges_by_follower_agent_id(
                follower_agent_id,
                conn=c,
            )

    @validate_inputs((validate_agent_id, "target_agent_id"))
    def count_agent_follow_edges_by_target_agent_id(
        self, target_agent_id: str, conn: object | None = None
    ) -> int:
        """Count follow edges where the given agent is the target."""
        if conn is not None:
            return self._db_adapter.count_agent_follow_edges_by_target_agent_id(
                target_agent_id,
                conn=conn,
            )
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.count_agent_follow_edges_by_target_agent_id(
                target_agent_id,
                conn=c,
            )

    @validate_inputs(
        (validate_agent_id, "follower_agent_id"),
        (validate_agent_id, "target_agent_id"),
    )
    def delete_agent_follow_edge(
        self,
        follower_agent_id: str,
        target_agent_id: str,
        conn: object | None = None,
    ) -> bool:
        """Delete a follow edge by its natural key."""
        if conn is not None:
            return self._db_adapter.delete_agent_follow_edge(
                follower_agent_id,
                target_agent_id,
                conn=conn,
            )
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.delete_agent_follow_edge(
                follower_agent_id,
                target_agent_id,
                conn=c,
            )


def create_sqlite_agent_follow_edge_repository(
    *,
    transaction_provider: TransactionProvider,
) -> SQLiteAgentFollowEdgeRepository:
    """Factory to create SQLiteAgentFollowEdgeRepository with default dependencies."""
    from db.adapters.sqlite import SQLiteAgentFollowEdgeAdapter

    return SQLiteAgentFollowEdgeRepository(
        db_adapter=SQLiteAgentFollowEdgeAdapter(),
        transaction_provider=transaction_provider,
    )


def _is_duplicate_agent_follow_edge_integrity_error(
    exc: sqlite3.IntegrityError,
) -> bool:
    """Return True when SQLite surfaced the natural-key uniqueness constraint."""
    message = str(exc)
    return (
        "uq_agent_follow_edges_follower_target" in message
        or (
            "UNIQUE constraint failed: agent_follow_edges.follower_agent_id,"
            " agent_follow_edges.target_agent_id"
        )
        in message
    )
