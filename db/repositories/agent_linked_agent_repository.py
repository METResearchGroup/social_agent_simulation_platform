"""SQLite implementation of agent linked agent repository."""

from collections.abc import Iterable

from db.adapters.base import AgentLinkedAgentDatabaseAdapter, TransactionProvider
from db.repositories.interfaces import AgentLinkedAgentRepository
from simulation.core.models.agent_linked_agent import AgentLinkedAgent


class SQLiteAgentLinkedAgentRepository(AgentLinkedAgentRepository):
    """SQLite implementation of AgentLinkedAgentRepository."""

    def __init__(
        self,
        *,
        db_adapter: AgentLinkedAgentDatabaseAdapter,
        transaction_provider: TransactionProvider,
    ):
        self._db_adapter = db_adapter
        self._transaction_provider = transaction_provider

    def create_linked_agents(
        self, linked_agents: list[AgentLinkedAgent], conn: object | None = None
    ) -> None:
        """Create agent linked agents (batch)."""
        if conn is not None:
            self._db_adapter.write_agent_linked_agents(linked_agents, conn=conn)
        else:
            with self._transaction_provider.run_transaction() as c:
                self._db_adapter.write_agent_linked_agents(linked_agents, conn=c)

    def get_linked_agents_by_agent_ids(
        self, agent_ids: Iterable[str]
    ) -> dict[str, list[AgentLinkedAgent]]:
        """Return linked agents per agent_id."""
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_agent_linked_agents_by_agent_ids(
                agent_ids, conn=c
            )


def create_sqlite_agent_linked_agent_repository(
    *,
    transaction_provider: TransactionProvider,
) -> SQLiteAgentLinkedAgentRepository:
    """Factory to create SQLiteAgentLinkedAgentRepository."""
    from db.adapters.sqlite import SQLiteAgentLinkedAgentAdapter

    return SQLiteAgentLinkedAgentRepository(
        db_adapter=SQLiteAgentLinkedAgentAdapter(),
        transaction_provider=transaction_provider,
    )
