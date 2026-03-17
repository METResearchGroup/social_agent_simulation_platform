"""SQLite implementation of immutable run-follow-edge snapshot repository."""

from db.adapters.base import RunFollowEdgeDatabaseAdapter, TransactionProvider
from db.repositories.interfaces import RunFollowEdgeRepository
from lib.validation_decorators import validate_inputs
from simulation.core.models.run_follow_edges import RunFollowEdgeSnapshot
from simulation.core.utils.validators import validate_run_id


class SQLiteRunFollowEdgeRepository(RunFollowEdgeRepository):
    """SQLite-backed repository for run_follow_edges snapshots."""

    def __init__(
        self,
        *,
        db_adapter: RunFollowEdgeDatabaseAdapter,
        transaction_provider: TransactionProvider,
    ):
        self._db_adapter = db_adapter
        self._transaction_provider = transaction_provider

    @validate_inputs((validate_run_id, "run_id"))
    def write_run_follow_edges(
        self,
        run_id: str,
        rows: list[RunFollowEdgeSnapshot],
        conn: object | None = None,
    ) -> None:
        if conn is not None:
            self._db_adapter.write_run_follow_edges(run_id, rows, conn=conn)
            return

        with self._transaction_provider.run_transaction() as c:
            self._db_adapter.write_run_follow_edges(run_id, rows, conn=c)

    @validate_inputs((validate_run_id, "run_id"))
    def list_run_follow_edges(self, run_id: str) -> list[RunFollowEdgeSnapshot]:
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_run_follow_edges_for_run(run_id, conn=c)


def create_sqlite_run_follow_edge_repository(
    *,
    transaction_provider: TransactionProvider,
) -> SQLiteRunFollowEdgeRepository:
    """Factory to create SQLiteRunFollowEdgeRepository with default dependencies."""
    from db.adapters.sqlite import SQLiteRunFollowEdgeAdapter

    return SQLiteRunFollowEdgeRepository(
        db_adapter=SQLiteRunFollowEdgeAdapter(),
        transaction_provider=transaction_provider,
    )
