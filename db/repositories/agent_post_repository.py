"""SQLite repository for editable seed-state agent posts."""

from db.adapters.base import AgentPostDatabaseAdapter, TransactionProvider
from db.repositories.interfaces import AgentPostRepository
from simulation.core.models.agent_posts import AgentPost


class SQLiteAgentPostRepository(AgentPostRepository):
    """SQLite implementation of AgentPostRepository."""

    def __init__(
        self,
        *,
        db_adapter: AgentPostDatabaseAdapter,
        transaction_provider: TransactionProvider,
    ):
        self._db_adapter = db_adapter
        self._transaction_provider = transaction_provider

    def write_agent_posts(
        self, posts: list[AgentPost], conn: object | None = None
    ) -> None:
        if not posts:
            return
        if conn is not None:
            self._db_adapter.write_agent_posts(posts, conn=conn)
            return
        with self._transaction_provider.run_transaction() as c:
            self._db_adapter.write_agent_posts(posts, conn=c)

    def upsert_imported_agent_posts(
        self, posts: list[AgentPost], conn: object | None = None
    ) -> None:
        if not posts:
            return
        if conn is not None:
            self._db_adapter.upsert_imported_agent_posts(posts, conn=conn)
            return
        with self._transaction_provider.run_transaction() as c:
            self._db_adapter.upsert_imported_agent_posts(posts, conn=c)

    def list_posts_for_agent_ids(self, agent_ids: list[str]) -> list[AgentPost]:
        if not agent_ids:
            return []
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_posts_for_agent_ids(agent_ids, conn=c)

    def count_posts_by_agent_ids(self, agent_ids: list[str]) -> dict[str, int]:
        if not agent_ids:
            return {}
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.count_posts_by_agent_ids(agent_ids, conn=c)

    def count_all_posts(self) -> int:
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.count_all_posts(conn=c)


def create_sqlite_agent_post_repository(
    *,
    transaction_provider: TransactionProvider,
) -> SQLiteAgentPostRepository:
    """Factory to create SQLiteAgentPostRepository with default dependencies."""
    from db.adapters.sqlite import SQLiteAgentPostAdapter

    return SQLiteAgentPostRepository(
        db_adapter=SQLiteAgentPostAdapter(),
        transaction_provider=transaction_provider,
    )
