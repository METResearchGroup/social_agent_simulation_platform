"""SQLite implementation of agent seed follow repository."""

from __future__ import annotations

from collections.abc import Iterable

from db.adapters.base import AgentSeedFollowDatabaseAdapter, TransactionProvider
from db.repositories.interfaces import AgentSeedFollowRepository
from simulation.core.models.agent_seed_actions import AgentSeedFollow


class SQLiteAgentSeedFollowRepository(AgentSeedFollowRepository):
    """SQLite implementation of AgentSeedFollowRepository."""

    def __init__(
        self,
        *,
        db_adapter: AgentSeedFollowDatabaseAdapter,
        transaction_provider: TransactionProvider,
    ):
        self._db_adapter = db_adapter
        self._transaction_provider = transaction_provider

    def write_agent_seed_follows(
        self,
        seed_follows: Iterable[AgentSeedFollow],
        conn: object | None = None,
    ) -> None:
        if conn is not None:
            self._db_adapter.write_agent_seed_follows(seed_follows, conn=conn)
        else:
            with self._transaction_provider.run_transaction() as c:
                self._db_adapter.write_agent_seed_follows(seed_follows, conn=c)

    def read_agent_seed_follows_by_agent_handles(
        self, agent_handles: Iterable[str]
    ) -> list[AgentSeedFollow]:
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_agent_seed_follows_by_agent_handles(
                agent_handles, conn=c
            )


def create_sqlite_agent_seed_follow_repository(
    *,
    transaction_provider: TransactionProvider,
) -> SQLiteAgentSeedFollowRepository:
    from db.adapters.sqlite.agent_seed_follow_adapter import (
        SQLiteAgentSeedFollowAdapter,
    )

    return SQLiteAgentSeedFollowRepository(
        db_adapter=SQLiteAgentSeedFollowAdapter(),
        transaction_provider=transaction_provider,
    )
