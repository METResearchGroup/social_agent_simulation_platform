"""SQLite implementation of immutable run-agent snapshot repository."""

from db.adapters.base import RunAgentDatabaseAdapter, TransactionProvider
from db.repositories.interfaces import RunAgentRepository
from lib.validation_decorators import validate_inputs
from simulation.core.models.run_agents import RunAgentSnapshot
from simulation.core.utils.validators import validate_run_id


class SQLiteRunAgentRepository(RunAgentRepository):
    """SQLite-backed repository for run_agents snapshots."""

    def __init__(
        self,
        *,
        db_adapter: RunAgentDatabaseAdapter,
        transaction_provider: TransactionProvider,
    ):
        self._db_adapter = db_adapter
        self._transaction_provider = transaction_provider

    @validate_inputs((validate_run_id, "run_id"))
    def write_run_agents(
        self,
        run_id: str,
        rows: list[RunAgentSnapshot],
        conn: object | None = None,
    ) -> None:
        if conn is not None:
            self._db_adapter.write_run_agents(run_id, rows, conn=conn)
            return

        with self._transaction_provider.run_transaction() as c:
            self._db_adapter.write_run_agents(run_id, rows, conn=c)

    @validate_inputs((validate_run_id, "run_id"))
    def list_run_agents(self, run_id: str) -> list[RunAgentSnapshot]:
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_run_agents_for_run(run_id, conn=c)


def create_sqlite_run_agent_repository(
    *,
    transaction_provider: TransactionProvider,
) -> SQLiteRunAgentRepository:
    """Factory to create SQLiteRunAgentRepository with default dependencies."""
    from db.adapters.sqlite import SQLiteRunAgentAdapter

    return SQLiteRunAgentRepository(
        db_adapter=SQLiteRunAgentAdapter(),
        transaction_provider=transaction_provider,
    )
