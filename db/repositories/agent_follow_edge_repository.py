"""SQLite repository for editable seed-state follow edges."""

import sqlite3

from db.adapters.base import AgentFollowEdgeDatabaseAdapter, TransactionProvider
from db.repositories.interfaces import AgentFollowEdgeRepository
from lib.validation_decorators import validate_inputs
from simulation.core.models.agent_follow_edge import (
    AgentFollowEdge,
    AgentFollowEdgePage,
)
from simulation.core.utils.exceptions import (
    DuplicateAgentFollowEdgeError,
    SelfFollowEdgeNotAllowedError,
)
from simulation.core.utils.validators import validate_agent_id


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

    def create_edge(
        self, edge: AgentFollowEdge, conn: object | None = None
    ) -> AgentFollowEdge:
        """Insert one follow edge row."""
        try:
            if conn is not None:
                self._db_adapter.write_agent_follow_edge(edge, conn=conn)
            else:
                with self._transaction_provider.run_transaction() as c:
                    self._db_adapter.write_agent_follow_edge(edge, conn=c)
        except sqlite3.IntegrityError as exc:
            _raise_follow_edge_write_error(exc, edge=edge)
        return edge

    @validate_inputs((validate_agent_id, "follower_agent_id"))
    def list_edges_by_follower_agent_id(
        self,
        follower_agent_id: str,
        *,
        limit: int,
        offset: int,
        conn: object | None = None,
    ) -> list[AgentFollowEdge]:
        """List follow edges for a follower in deterministic order."""
        if conn is not None:
            return self._db_adapter.read_edges_by_follower_agent_id(
                follower_agent_id,
                limit=limit,
                offset=offset,
                conn=conn,
            )
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_edges_by_follower_agent_id(
                follower_agent_id,
                limit=limit,
                offset=offset,
                conn=c,
            )

    @validate_inputs((validate_agent_id, "follower_agent_id"))
    def get_edge_page_by_follower_agent_id(
        self,
        follower_agent_id: str,
        *,
        limit: int,
        offset: int,
        conn: object | None = None,
    ) -> AgentFollowEdgePage:
        """Read a consistent page of follow edges with resolved target handles."""
        if conn is not None:
            return self._db_adapter.read_edge_page_by_follower_agent_id(
                follower_agent_id,
                limit=limit,
                offset=offset,
                conn=conn,
            )
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_edge_page_by_follower_agent_id(
                follower_agent_id,
                limit=limit,
                offset=offset,
                conn=c,
            )

    @validate_inputs((validate_agent_id, "follower_agent_id"))
    def count_edges_by_follower_agent_id(
        self, follower_agent_id: str, conn: object | None = None
    ) -> int:
        """Count outgoing follow edges for a follower agent."""
        if conn is not None:
            return self._db_adapter.count_edges_by_follower_agent_id(
                follower_agent_id,
                conn=conn,
            )
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.count_edges_by_follower_agent_id(
                follower_agent_id,
                conn=c,
            )

    @validate_inputs((validate_agent_id, "target_agent_id"))
    def count_edges_by_target_agent_id(
        self, target_agent_id: str, conn: object | None = None
    ) -> int:
        """Count incoming follow edges for a target agent."""
        if conn is not None:
            return self._db_adapter.count_edges_by_target_agent_id(
                target_agent_id,
                conn=conn,
            )
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.count_edges_by_target_agent_id(
                target_agent_id,
                conn=c,
            )

    @validate_inputs(
        (validate_agent_id, "follower_agent_id"),
        (validate_agent_id, "target_agent_id"),
    )
    def delete_edge(
        self,
        follower_agent_id: str,
        target_agent_id: str,
        conn: object | None = None,
    ) -> bool:
        """Delete one follow edge and return whether a row was removed."""
        if conn is not None:
            return self._db_adapter.delete_edge(
                follower_agent_id,
                target_agent_id,
                conn=conn,
            )
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.delete_edge(
                follower_agent_id,
                target_agent_id,
                conn=c,
            )

    @validate_inputs((validate_agent_id, "agent_id"))
    def list_connected_agent_ids(
        self, agent_id: str, conn: object | None = None
    ) -> list[str]:
        """List distinct agent_ids connected to the given agent by any follow edge."""
        if conn is not None:
            return self._db_adapter.read_connected_agent_ids(agent_id, conn=conn)
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_connected_agent_ids(agent_id, conn=c)

    @validate_inputs((validate_agent_id, "agent_id"))
    def delete_edges_for_agent(self, agent_id: str, conn: object | None = None) -> None:
        """Delete all follow edges where the agent participates."""
        if conn is not None:
            self._db_adapter.delete_edges_for_agent(agent_id, conn=conn)
        else:
            with self._transaction_provider.run_transaction() as c:
                self._db_adapter.delete_edges_for_agent(agent_id, conn=c)


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


def _raise_follow_edge_write_error(
    exc: sqlite3.IntegrityError, *, edge: AgentFollowEdge
) -> None:
    """Translate SQLite constraint failures into stable domain exceptions."""
    message = str(exc)
    if (
        "UNIQUE constraint failed" in message
        or "uq_agent_follow_edges_follower_target" in message
    ):
        raise DuplicateAgentFollowEdgeError(
            edge.follower_agent_id,
            edge.target_agent_id,
        ) from exc
    if (
        "CHECK constraint failed" in message
        or "ck_agent_follow_edges_no_self_follow" in message
    ):
        raise SelfFollowEdgeNotAllowedError(edge.follower_agent_id) from exc
    raise exc
