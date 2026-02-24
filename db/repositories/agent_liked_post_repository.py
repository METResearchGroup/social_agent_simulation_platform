"""SQLite implementation of agent liked post repository."""

from collections.abc import Iterable

from db.adapters.base import AgentLikedPostDatabaseAdapter, TransactionProvider
from db.repositories.interfaces import AgentLikedPostRepository
from simulation.core.models.agent_liked_post import AgentLikedPost


class SQLiteAgentLikedPostRepository(AgentLikedPostRepository):
    """SQLite implementation of AgentLikedPostRepository."""

    def __init__(
        self,
        *,
        db_adapter: AgentLikedPostDatabaseAdapter,
        transaction_provider: TransactionProvider,
    ):
        self._db_adapter = db_adapter
        self._transaction_provider = transaction_provider

    def create_liked_posts(
        self, liked_posts: list[AgentLikedPost], conn: object | None = None
    ) -> None:
        """Create agent liked posts (batch)."""
        if conn is not None:
            self._db_adapter.write_agent_liked_posts(liked_posts, conn=conn)
        else:
            with self._transaction_provider.run_transaction() as c:
                self._db_adapter.write_agent_liked_posts(liked_posts, conn=c)

    def get_liked_posts_by_agent_ids(
        self, agent_ids: Iterable[str]
    ) -> dict[str, list[AgentLikedPost]]:
        """Return liked posts per agent_id."""
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_agent_liked_posts_by_agent_ids(
                agent_ids, conn=c
            )


def create_sqlite_agent_liked_post_repository(
    *,
    transaction_provider: TransactionProvider,
) -> SQLiteAgentLikedPostRepository:
    """Factory to create SQLiteAgentLikedPostRepository."""
    from db.adapters.sqlite import SQLiteAgentLikedPostAdapter

    return SQLiteAgentLikedPostRepository(
        db_adapter=SQLiteAgentLikedPostAdapter(),
        transaction_provider=transaction_provider,
    )
