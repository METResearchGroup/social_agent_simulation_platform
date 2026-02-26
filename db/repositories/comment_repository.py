"""SQLite implementation of comment action repository."""

from __future__ import annotations

from collections.abc import Iterable

from db.adapters.base import CommentDatabaseAdapter, TransactionProvider
from db.repositories.interfaces import CommentRepository
from simulation.core.models.generated.comment import GeneratedComment
from simulation.core.models.persisted_actions import PersistedComment


class SQLiteCommentRepository(CommentRepository):
    """SQLite implementation of CommentRepository."""

    def __init__(
        self,
        *,
        db_adapter: CommentDatabaseAdapter,
        transaction_provider: TransactionProvider,
    ):
        self._db_adapter = db_adapter
        self._transaction_provider = transaction_provider

    def write_comments(
        self,
        run_id: str,
        turn_number: int,
        comments: Iterable[GeneratedComment],
        conn: object | None = None,
    ) -> None:
        if conn is not None:
            self._db_adapter.write_comments(run_id, turn_number, comments, conn=conn)
        else:
            with self._transaction_provider.run_transaction() as c:
                self._db_adapter.write_comments(run_id, turn_number, comments, conn=c)

    def read_comments_by_run_turn(
        self, run_id: str, turn_number: int
    ) -> list[PersistedComment]:
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_comments_by_run_turn(
                run_id, turn_number, conn=c
            )


def create_sqlite_comment_repository(
    *,
    transaction_provider: TransactionProvider,
) -> SQLiteCommentRepository:
    from db.adapters.sqlite.comment_adapter import SQLiteCommentAdapter

    return SQLiteCommentRepository(
        db_adapter=SQLiteCommentAdapter(),
        transaction_provider=transaction_provider,
    )
