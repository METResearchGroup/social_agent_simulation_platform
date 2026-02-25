"""SQLite implementation of like action repository."""

from __future__ import annotations

from collections.abc import Iterable

from db.adapters.base import LikeDatabaseAdapter, TransactionProvider
from db.repositories.interfaces import LikeRepository
from simulation.core.models.generated.like import GeneratedLike
from simulation.core.models.persisted_actions import PersistedLike


class SQLiteLikeRepository(LikeRepository):
    """SQLite implementation of LikeRepository."""

    def __init__(
        self,
        *,
        db_adapter: LikeDatabaseAdapter,
        transaction_provider: TransactionProvider,
    ):
        self._db_adapter = db_adapter
        self._transaction_provider = transaction_provider

    def write_likes(
        self,
        run_id: str,
        turn_number: int,
        likes: Iterable[GeneratedLike],
        conn: object | None = None,
    ) -> None:
        if conn is not None:
            self._db_adapter.write_likes(run_id, turn_number, likes, conn=conn)
        else:
            with self._transaction_provider.run_transaction() as c:
                self._db_adapter.write_likes(run_id, turn_number, likes, conn=c)

    def read_likes_by_run_turn(
        self, run_id: str, turn_number: int
    ) -> list[PersistedLike]:
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_likes_by_run_turn(run_id, turn_number, conn=c)


def create_sqlite_like_repository(
    *,
    transaction_provider: TransactionProvider,
) -> SQLiteLikeRepository:
    from db.adapters.sqlite.like_adapter import SQLiteLikeAdapter

    return SQLiteLikeRepository(
        db_adapter=SQLiteLikeAdapter(),
        transaction_provider=transaction_provider,
    )
