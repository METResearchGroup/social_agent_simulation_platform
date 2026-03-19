"""SQLite-backed repository for immutable run-start seeded likes."""

from collections.abc import Iterable

from db.adapters.base import RunPostLikeDatabaseAdapter, TransactionProvider
from db.adapters.sqlite.run_post_like_adapter import SQLiteRunPostLikeAdapter
from db.repositories.interfaces import RunPostLikeRepository
from lib.validation_decorators import validate_inputs
from simulation.core.models.run_post_likes import RunPostLikeSnapshot
from simulation.core.utils.validators import validate_run_id


class SQLiteRunPostLikeRepository(RunPostLikeRepository):
    """SQLite-backed repository for run_post_likes rows."""

    def __init__(
        self,
        *,
        db_adapter: RunPostLikeDatabaseAdapter,
        transaction_provider: TransactionProvider,
    ):
        self._db_adapter = db_adapter
        self._transaction_provider = transaction_provider

    @validate_inputs((validate_run_id, "run_id"))
    def write_run_post_likes(
        self,
        run_id: str,
        rows: list[RunPostLikeSnapshot],
        conn: object | None = None,
    ) -> None:
        if conn is not None:
            self._db_adapter.write_run_post_likes(run_id, rows, conn=conn)
            return

        with self._transaction_provider.run_transaction() as c:
            self._db_adapter.write_run_post_likes(run_id, rows, conn=c)

    @validate_inputs((validate_run_id, "run_id"))
    def count_likes_by_run_post_ids(
        self,
        run_id: str,
        run_post_ids: Iterable[str],
        conn: object | None = None,
    ) -> dict[str, int]:
        if conn is not None:
            return self._db_adapter.count_likes_by_run_post_ids(
                run_id, run_post_ids, conn=conn
            )

        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.count_likes_by_run_post_ids(
                run_id, run_post_ids, conn=c
            )


def create_sqlite_run_post_like_repository(
    *,
    transaction_provider: TransactionProvider,
) -> SQLiteRunPostLikeRepository:
    """Factory to create SQLiteRunPostLikeRepository with default dependencies."""
    return SQLiteRunPostLikeRepository(
        db_adapter=SQLiteRunPostLikeAdapter(),
        transaction_provider=transaction_provider,
    )
