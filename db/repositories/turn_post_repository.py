"""SQLite implementation of turn post repository."""

from collections.abc import Iterable

from db.adapters.base import TransactionProvider, TurnPostDatabaseAdapter
from db.repositories.interfaces import TurnPostRepository
from lib.validation_decorators import validate_inputs
from simulation.core.models.turn_posts import TurnPostSnapshot
from simulation.core.utils.validators import validate_run_id, validate_turn_number


class SQLiteTurnPostRepository(TurnPostRepository):
    """SQLite-backed repository for ``turn_posts``."""

    def __init__(
        self,
        *,
        db_adapter: TurnPostDatabaseAdapter,
        transaction_provider: TransactionProvider,
    ):
        self._db_adapter = db_adapter
        self._transaction_provider = transaction_provider

    @validate_inputs((validate_run_id, "run_id"))
    def read_turn_posts_by_ids(
        self, run_id: str, post_ids: Iterable[str]
    ) -> list[TurnPostSnapshot]:
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_turn_posts_by_ids(run_id, post_ids, conn=c)

    @validate_inputs(
        (validate_run_id, "run_id"), (validate_turn_number, "before_turn_number")
    )
    def list_turn_posts_for_run_before_turn(
        self, run_id: str, before_turn_number: int
    ) -> list[TurnPostSnapshot]:
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.list_turn_posts_for_run_before_turn(
                run_id, before_turn_number, conn=c
            )

    @validate_inputs((validate_run_id, "run_id"), (validate_turn_number, "turn_number"))
    def list_turn_posts_for_run_at_turn(
        self, run_id: str, turn_number: int
    ) -> list[TurnPostSnapshot]:
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.list_turn_posts_for_run_at_turn(
                run_id, turn_number, conn=c
            )

    @validate_inputs((validate_run_id, "run_id"), (validate_turn_number, "turn_number"))
    def write_turn_posts(
        self,
        run_id: str,
        turn_number: int,
        rows: list[TurnPostSnapshot],
        conn: object | None = None,
    ) -> None:
        if conn is not None:
            self._db_adapter.write_turn_posts(run_id, turn_number, rows, conn=conn)
        else:
            with self._transaction_provider.run_transaction() as c:
                self._db_adapter.write_turn_posts(run_id, turn_number, rows, conn=c)


def create_sqlite_turn_post_repository(
    *,
    transaction_provider: TransactionProvider,
) -> SQLiteTurnPostRepository:
    """Factory to create SQLiteTurnPostRepository with default dependencies."""
    from db.adapters.sqlite.turn_post_adapter import SQLiteTurnPostAdapter

    return SQLiteTurnPostRepository(
        db_adapter=SQLiteTurnPostAdapter(),
        transaction_provider=transaction_provider,
    )
