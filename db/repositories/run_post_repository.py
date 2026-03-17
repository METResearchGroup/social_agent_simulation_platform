"""SQLite implementation of immutable run-post snapshot repository."""

from collections.abc import Iterable

from db.adapters.base import RunPostDatabaseAdapter, TransactionProvider
from db.repositories.interfaces import RunPostRepository
from lib.validation_decorators import validate_inputs
from simulation.core.models.run_posts import RunPostSnapshot
from simulation.core.utils.validators import validate_run_id


class SQLiteRunPostRepository(RunPostRepository):
    """SQLite-backed repository for run_posts snapshots."""

    def __init__(
        self,
        *,
        db_adapter: RunPostDatabaseAdapter,
        transaction_provider: TransactionProvider,
    ):
        self._db_adapter = db_adapter
        self._transaction_provider = transaction_provider

    @validate_inputs((validate_run_id, "run_id"))
    def write_run_posts(
        self,
        run_id: str,
        rows: list[RunPostSnapshot],
        conn: object | None = None,
    ) -> None:
        if conn is not None:
            self._db_adapter.write_run_posts(run_id, rows, conn=conn)
            return

        with self._transaction_provider.run_transaction() as c:
            self._db_adapter.write_run_posts(run_id, rows, conn=c)

    @validate_inputs((validate_run_id, "run_id"))
    def list_run_posts(self, run_id: str) -> list[RunPostSnapshot]:
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_run_posts_for_run(run_id, conn=c)

    @validate_inputs((validate_run_id, "run_id"))
    def read_run_posts_by_ids(
        self, run_id: str, post_ids: Iterable[str]
    ) -> list[RunPostSnapshot]:
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_run_posts_by_ids(run_id, post_ids, conn=c)


def create_sqlite_run_post_repository(
    *,
    transaction_provider: TransactionProvider,
) -> SQLiteRunPostRepository:
    """Factory to create SQLiteRunPostRepository with default dependencies."""
    from db.adapters.sqlite import SQLiteRunPostAdapter

    return SQLiteRunPostRepository(
        db_adapter=SQLiteRunPostAdapter(),
        transaction_provider=transaction_provider,
    )
