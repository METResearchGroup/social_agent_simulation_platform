"""SQLite implementation of agent seed like repository."""

from __future__ import annotations

from collections.abc import Iterable

from db.adapters.base import AgentSeedLikeDatabaseAdapter, TransactionProvider
from db.repositories.interfaces import AgentSeedLikeRepository
from simulation.core.models.agent_seed_actions import AgentSeedLike


class SQLiteAgentSeedLikeRepository(AgentSeedLikeRepository):
    """SQLite implementation of AgentSeedLikeRepository."""

    def __init__(
        self,
        *,
        db_adapter: AgentSeedLikeDatabaseAdapter,
        transaction_provider: TransactionProvider,
    ):
        self._db_adapter = db_adapter
        self._transaction_provider = transaction_provider

    def write_agent_seed_likes(
        self,
        seed_likes: Iterable[AgentSeedLike],
        conn: object | None = None,
    ) -> None:
        if conn is not None:
            self._db_adapter.write_agent_seed_likes(seed_likes, conn=conn)
        else:
            with self._transaction_provider.run_transaction() as c:
                self._db_adapter.write_agent_seed_likes(seed_likes, conn=c)

    def read_agent_seed_likes_by_agent_handles(
        self, agent_handles: Iterable[str]
    ) -> list[AgentSeedLike]:
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_agent_seed_likes_by_agent_handles(
                agent_handles, conn=c
            )


def create_sqlite_agent_seed_like_repository(
    *,
    transaction_provider: TransactionProvider,
) -> SQLiteAgentSeedLikeRepository:
    from db.adapters.sqlite.agent_seed_like_adapter import SQLiteAgentSeedLikeAdapter

    return SQLiteAgentSeedLikeRepository(
        db_adapter=SQLiteAgentSeedLikeAdapter(),
        transaction_provider=transaction_provider,
    )
