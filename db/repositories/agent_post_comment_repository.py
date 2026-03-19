"""SQLite-backed repository for editable seed-state agent_post_comments."""

from collections.abc import Iterable

from db.adapters.base import AgentPostCommentDatabaseAdapter, TransactionProvider
from db.adapters.sqlite.agent_post_comment_adapter import SQLiteAgentPostCommentAdapter
from db.repositories.interfaces import AgentPostCommentRepository
from simulation.core.models.agent_post_comments import AgentPostComment


class SQLiteAgentPostCommentRepository(AgentPostCommentRepository):
    """SQLite-backed repository for agent_post_comments rows."""

    def __init__(
        self,
        *,
        db_adapter: AgentPostCommentDatabaseAdapter,
        transaction_provider: TransactionProvider,
    ):
        self._db_adapter = db_adapter
        self._transaction_provider = transaction_provider

    def write_agent_post_comments(
        self,
        rows: list[AgentPostComment],
        conn: object | None = None,
    ) -> None:
        if conn is not None:
            self._db_adapter.write_agent_post_comments(rows, conn=conn)
            return

        with self._transaction_provider.run_transaction() as c:
            self._db_adapter.write_agent_post_comments(rows, conn=c)

    def list_comments_for_agent_post_ids(
        self,
        agent_post_ids: Iterable[str],
        conn: object | None = None,
    ) -> list[AgentPostComment]:
        if conn is not None:
            return self._db_adapter.list_comments_for_agent_post_ids(
                agent_post_ids, conn=conn
            )

        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.list_comments_for_agent_post_ids(
                agent_post_ids, conn=c
            )


def create_sqlite_agent_post_comment_repository(
    *,
    transaction_provider: TransactionProvider,
) -> SQLiteAgentPostCommentRepository:
    """Factory to create SQLiteAgentPostCommentRepository with default dependencies."""
    return SQLiteAgentPostCommentRepository(
        db_adapter=SQLiteAgentPostCommentAdapter(),
        transaction_provider=transaction_provider,
    )
