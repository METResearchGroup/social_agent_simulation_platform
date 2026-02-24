"""SQLite implementation of agent bio repositories."""

from db.adapters.base import AgentBioDatabaseAdapter, TransactionProvider
from db.repositories.interfaces import AgentBioRepository
from lib.validation_decorators import validate_inputs
from simulation.core.models.agent_bio import AgentBio
from simulation.core.validators import validate_agent_id


class SQLiteAgentBioRepository(AgentBioRepository):
    """SQLite implementation of AgentBioRepository."""

    def __init__(
        self,
        *,
        db_adapter: AgentBioDatabaseAdapter,
        transaction_provider: TransactionProvider,
    ):
        """Initialize repository with injected dependencies."""
        self._db_adapter = db_adapter
        self._transaction_provider = transaction_provider

    def create_agent_bio(self, bio: AgentBio, conn: object | None = None) -> AgentBio:
        """Create an agent bio in SQLite."""
        if conn is not None:
            self._db_adapter.write_agent_bio(bio, conn=conn)
        else:
            with self._transaction_provider.run_transaction() as c:
                self._db_adapter.write_agent_bio(bio, conn=c)
        return bio

    @validate_inputs((validate_agent_id, "agent_id"))
    def get_latest_agent_bio(self, agent_id: str) -> AgentBio | None:
        """Get the latest bio for an agent."""
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_latest_agent_bio(agent_id, conn=c)

    @validate_inputs((validate_agent_id, "agent_id"))
    def list_agent_bios(self, agent_id: str) -> list[AgentBio]:
        """List all bios for an agent, ordered by created_at DESC."""
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_agent_bios_by_agent_id(agent_id, conn=c)


def create_sqlite_agent_bio_repository(
    *,
    transaction_provider: TransactionProvider,
) -> SQLiteAgentBioRepository:
    """Factory to create SQLiteAgentBioRepository with default dependencies."""
    from db.adapters.sqlite import SQLiteAgentBioAdapter

    return SQLiteAgentBioRepository(
        db_adapter=SQLiteAgentBioAdapter(),
        transaction_provider=transaction_provider,
    )
