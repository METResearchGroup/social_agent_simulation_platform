"""SQLite-backed repository for editable seed-state agent_post_likes."""

from collections.abc import Iterable

from db.adapters.base import AgentPostLikeDatabaseAdapter, TransactionProvider
from db.adapters.sqlite.agent_post_like_adapter import SQLiteAgentPostLikeAdapter
from db.repositories.interfaces import AgentPostLikeRepository
from simulation.core.models.agent_post_likes import AgentPostLike


class SQLiteAgentPostLikeRepository(AgentPostLikeRepository):
    """SQLite-backed repository for agent_post_likes rows."""

    def __init__(
        self,
        *,
        db_adapter: AgentPostLikeDatabaseAdapter,
        transaction_provider: TransactionProvider,
    ):
        self._db_adapter = db_adapter
        self._transaction_provider = transaction_provider

    def write_agent_post_likes(
        self,
        rows: list[AgentPostLike],
        conn: object | None = None,
    ) -> None:
        # Note: rows should be a list[AgentPostLike] by interface contract.
        if conn is not None:
            self._db_adapter.write_agent_post_likes(rows, conn=conn)
            return

        with self._transaction_provider.run_transaction() as c:
            self._db_adapter.write_agent_post_likes(rows, conn=c)

    def list_likes_for_agent_post_ids(
        self,
        agent_post_ids: Iterable[str],
        conn: object | None = None,
    ) -> list[AgentPostLike]:
        if conn is not None:
            return self._db_adapter.list_likes_for_agent_post_ids(
                agent_post_ids, conn=conn
            )

        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.list_likes_for_agent_post_ids(
                agent_post_ids, conn=c
            )


def create_sqlite_agent_post_like_repository(
    *,
    transaction_provider: TransactionProvider,
) -> SQLiteAgentPostLikeRepository:
    """Factory to create SQLiteAgentPostLikeRepository with default dependencies."""
    return SQLiteAgentPostLikeRepository(
        db_adapter=SQLiteAgentPostLikeAdapter(),
        transaction_provider=transaction_provider,
    )
