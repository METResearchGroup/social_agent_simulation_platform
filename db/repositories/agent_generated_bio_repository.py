"""SQLite repository for agent-generated bios."""

from collections.abc import Iterable

from db.adapters.base import AgentGeneratedBioDatabaseAdapter, TransactionProvider
from db.repositories.interfaces import AgentGeneratedBioRepository
from simulation.core.models.agent_generated_bio import AgentGeneratedBio


class SQLiteAgentGeneratedBioRepository(AgentGeneratedBioRepository):
    """SQLite implementation of AgentGeneratedBioRepository."""

    def __init__(
        self,
        *,
        db_adapter: AgentGeneratedBioDatabaseAdapter,
        transaction_provider: TransactionProvider,
    ):
        self._db_adapter = db_adapter
        self._transaction_provider = transaction_provider

    def create_agent_generated_bio(
        self, bio: AgentGeneratedBio, conn: object | None = None
    ) -> AgentGeneratedBio:
        if conn is not None:
            self._db_adapter.write_agent_generated_bio(bio, conn=conn)
        else:
            with self._transaction_provider.run_transaction() as c:
                self._db_adapter.write_agent_generated_bio(bio, conn=c)
        return bio

    def get_latest_agent_generated_bio(self, agent_id: str) -> AgentGeneratedBio | None:
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_latest_agent_generated_bio(agent_id, conn=c)

    def list_agent_generated_bios(self, agent_id: str) -> list[AgentGeneratedBio]:
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.list_agent_generated_bios(agent_id, conn=c)

    def get_latest_generated_bios_by_agent_ids(
        self, agent_ids: Iterable[str]
    ) -> dict[str, AgentGeneratedBio | None]:
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_latest_agent_generated_bios_by_agent_ids(
                agent_ids, conn=c
            )


def create_sqlite_agent_generated_bio_repository(
    *,
    transaction_provider: TransactionProvider,
) -> SQLiteAgentGeneratedBioRepository:
    """Factory for SQLiteAgentGeneratedBioRepository."""
    from db.adapters.sqlite import SQLiteAgentGeneratedBioAdapter

    return SQLiteAgentGeneratedBioRepository(
        db_adapter=SQLiteAgentGeneratedBioAdapter(),
        transaction_provider=transaction_provider,
    )
