"""SQLite implementation of follow action repository."""

from __future__ import annotations

from collections.abc import Iterable

from db.adapters.base import FollowDatabaseAdapter, TransactionProvider
from db.repositories.interfaces import FollowRepository
from simulation.core.models.generated.follow import GeneratedFollow
from simulation.core.models.persisted_actions import PersistedFollow


class SQLiteFollowRepository(FollowRepository):
    """SQLite implementation of FollowRepository."""

    def __init__(
        self,
        *,
        db_adapter: FollowDatabaseAdapter,
        transaction_provider: TransactionProvider,
    ):
        self._db_adapter = db_adapter
        self._transaction_provider = transaction_provider

    def write_follows(
        self,
        run_id: str,
        turn_number: int,
        follows: Iterable[GeneratedFollow],
        conn: object | None = None,
    ) -> None:
        if conn is not None:
            self._db_adapter.write_follows(run_id, turn_number, follows, conn=conn)
        else:
            with self._transaction_provider.run_transaction() as c:
                self._db_adapter.write_follows(run_id, turn_number, follows, conn=c)

    def read_follows_by_run_turn(
        self, run_id: str, turn_number: int
    ) -> list[PersistedFollow]:
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_follows_by_run_turn(
                run_id, turn_number, conn=c
            )


def create_sqlite_follow_repository(
    *,
    transaction_provider: TransactionProvider,
) -> SQLiteFollowRepository:
    from db.adapters.sqlite.follow_adapter import SQLiteFollowAdapter

    return SQLiteFollowRepository(
        db_adapter=SQLiteFollowAdapter(),
        transaction_provider=transaction_provider,
    )
