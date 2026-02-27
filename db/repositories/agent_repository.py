"""SQLite implementation of agent repositories."""

from db.adapters.base import AgentDatabaseAdapter, TransactionProvider
from db.repositories.interfaces import AgentRepository
from lib.validation_decorators import validate_inputs
from simulation.core.models.agent import Agent
from simulation.core.utils.validators import validate_agent_id, validate_handle_exists


class SQLiteAgentRepository(AgentRepository):
    """SQLite implementation of AgentRepository."""

    def __init__(
        self,
        *,
        db_adapter: AgentDatabaseAdapter,
        transaction_provider: TransactionProvider,
    ):
        """Initialize repository with injected dependencies."""
        self._db_adapter = db_adapter
        self._transaction_provider = transaction_provider

    def create_or_update_agent(self, agent: Agent, conn: object | None = None) -> Agent:
        """Create or update an agent in SQLite."""
        if conn is not None:
            self._db_adapter.write_agent(agent, conn=conn)
        else:
            with self._transaction_provider.run_transaction() as c:
                self._db_adapter.write_agent(agent, conn=c)
        return agent

    @validate_inputs((validate_agent_id, "agent_id"))
    def get_agent(self, agent_id: str) -> Agent | None:
        """Get an agent by ID."""
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_agent(agent_id, conn=c)

    @validate_inputs((validate_handle_exists, "handle"))
    def get_agent_by_handle(self, handle: str) -> Agent | None:
        """Get an agent by handle."""
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_agent_by_handle(handle, conn=c)

    def list_all_agents(self) -> list[Agent]:
        """List all agents, ordered by updated_at DESC and handle ASC."""
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_all_agents(conn=c)

    def list_agents_page(self, *, limit: int, offset: int) -> list[Agent]:
        """List a page of agents, ordered by updated_at DESC and handle ASC."""
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_agents_page(limit=limit, offset=offset, conn=c)

    def search_agents_page(
        self, *, handle_like: str, limit: int, offset: int
    ) -> list[Agent]:
        """List a page of agents filtered by handle LIKE, ordered by updated_at DESC, handle ASC."""
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_agents_page_by_handle_like(
                handle_like=handle_like, limit=limit, offset=offset, conn=c
            )


def create_sqlite_agent_repository(
    *,
    transaction_provider: TransactionProvider,
) -> SQLiteAgentRepository:
    """Factory to create SQLiteAgentRepository with default dependencies."""
    from db.adapters.sqlite import SQLiteAgentAdapter

    return SQLiteAgentRepository(
        db_adapter=SQLiteAgentAdapter(),
        transaction_provider=transaction_provider,
    )
