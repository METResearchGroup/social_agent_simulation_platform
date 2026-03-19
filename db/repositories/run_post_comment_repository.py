"""SQLite-backed repository for immutable run-start seeded comments."""

from collections.abc import Iterable

from db.adapters.base import RunPostCommentDatabaseAdapter, TransactionProvider
from db.adapters.sqlite.run_post_comment_adapter import SQLiteRunPostCommentAdapter
from db.repositories.interfaces import RunPostCommentRepository
from lib.validation_decorators import validate_inputs
from simulation.core.models.run_post_comments import RunPostCommentSnapshot
from simulation.core.utils.validators import validate_run_id


class SQLiteRunPostCommentRepository(RunPostCommentRepository):
    """SQLite-backed repository for run_post_comments rows."""

    def __init__(
        self,
        *,
        db_adapter: RunPostCommentDatabaseAdapter,
        transaction_provider: TransactionProvider,
    ):
        self._db_adapter = db_adapter
        self._transaction_provider = transaction_provider

    @validate_inputs((validate_run_id, "run_id"))
    def write_run_post_comments(
        self,
        run_id: str,
        rows: list[RunPostCommentSnapshot],
        conn: object | None = None,
    ) -> None:
        if conn is not None:
            self._db_adapter.write_run_post_comments(run_id, rows, conn=conn)
            return

        with self._transaction_provider.run_transaction() as c:
            self._db_adapter.write_run_post_comments(run_id, rows, conn=c)

    @validate_inputs((validate_run_id, "run_id"))
    def count_comments_by_run_post_ids(
        self,
        run_id: str,
        run_post_ids: Iterable[str],
        conn: object | None = None,
    ) -> dict[str, int]:
        if conn is not None:
            return self._db_adapter.count_comments_by_run_post_ids(
                run_id, run_post_ids, conn=conn
            )

        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.count_comments_by_run_post_ids(
                run_id, run_post_ids, conn=c
            )


def create_sqlite_run_post_comment_repository(
    *,
    transaction_provider: TransactionProvider,
) -> SQLiteRunPostCommentRepository:
    """Factory to create SQLiteRunPostCommentRepository with default dependencies."""
    return SQLiteRunPostCommentRepository(
        db_adapter=SQLiteRunPostCommentAdapter(),
        transaction_provider=transaction_provider,
    )
