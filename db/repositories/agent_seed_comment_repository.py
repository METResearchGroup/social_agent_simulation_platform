"""SQLite implementation of agent seed comment repository."""

from __future__ import annotations

from collections.abc import Iterable

from db.adapters.base import AgentSeedCommentDatabaseAdapter, TransactionProvider
from db.repositories.interfaces import AgentSeedCommentRepository
from simulation.core.models.agent_seed_actions import AgentSeedComment


class SQLiteAgentSeedCommentRepository(AgentSeedCommentRepository):
    """SQLite implementation of AgentSeedCommentRepository."""

    def __init__(
        self,
        *,
        db_adapter: AgentSeedCommentDatabaseAdapter,
        transaction_provider: TransactionProvider,
    ):
        self._db_adapter = db_adapter
        self._transaction_provider = transaction_provider

    def write_agent_seed_comments(
        self,
        seed_comments: Iterable[AgentSeedComment],
        conn: object | None = None,
    ) -> None:
        if conn is not None:
            self._db_adapter.write_agent_seed_comments(seed_comments, conn=conn)
        else:
            with self._transaction_provider.run_transaction() as c:
                self._db_adapter.write_agent_seed_comments(seed_comments, conn=c)

    def read_agent_seed_comments_by_agent_handles(
        self, agent_handles: Iterable[str]
    ) -> list[AgentSeedComment]:
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_agent_seed_comments_by_agent_handles(
                agent_handles, conn=c
            )


def create_sqlite_agent_seed_comment_repository(
    *,
    transaction_provider: TransactionProvider,
) -> SQLiteAgentSeedCommentRepository:
    from db.adapters.sqlite.agent_seed_comment_adapter import (
        SQLiteAgentSeedCommentAdapter,
    )

    return SQLiteAgentSeedCommentRepository(
        db_adapter=SQLiteAgentSeedCommentAdapter(),
        transaction_provider=transaction_provider,
    )
