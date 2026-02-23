"""SQLite implementation of agent repositories."""

from db.adapters.base import AgentDatabaseAdapter
from db.repositories.interfaces import AgentRepository
from lib.validation_decorators import validate_inputs
from simulation.core.models.agent import Agent
from simulation.core.validators import validate_agent_id, validate_handle_exists


class SQLiteAgentRepository(AgentRepository):
    """SQLite implementation of AgentRepository."""

    def __init__(self, db_adapter: AgentDatabaseAdapter):
        """Initialize repository with injected dependencies."""
        self._db_adapter = db_adapter

    def create_or_update_agent(self, agent: Agent) -> Agent:
        """Create or update an agent in SQLite."""
        self._db_adapter.write_agent(agent)
        return agent

    @validate_inputs((validate_agent_id, "agent_id"))
    def get_agent(self, agent_id: str) -> Agent | None:
        """Get an agent by ID."""
        return self._db_adapter.read_agent(agent_id)

    @validate_inputs((validate_handle_exists, "handle"))
    def get_agent_by_handle(self, handle: str) -> Agent | None:
        """Get an agent by handle."""
        return self._db_adapter.read_agent_by_handle(handle)

    def list_all_agents(self) -> list[Agent]:
        """List all agents, ordered by handle."""
        return self._db_adapter.read_all_agents()


def create_sqlite_agent_repository() -> SQLiteAgentRepository:
    """Factory to create SQLiteAgentRepository with default dependencies."""
    from db.adapters.sqlite import SQLiteAgentAdapter

    return SQLiteAgentRepository(db_adapter=SQLiteAgentAdapter())
