"""SQLite implementation of agent profile comment repository."""

from collections.abc import Iterable

from db.adapters.base import AgentProfileCommentDatabaseAdapter, TransactionProvider
from db.repositories.interfaces import AgentProfileCommentRepository
from simulation.core.models.agent_profile_comment import AgentProfileComment


class SQLiteAgentProfileCommentRepository(AgentProfileCommentRepository):
    """SQLite implementation of AgentProfileCommentRepository."""

    def __init__(
        self,
        *,
        db_adapter: AgentProfileCommentDatabaseAdapter,
        transaction_provider: TransactionProvider,
    ):
        self._db_adapter = db_adapter
        self._transaction_provider = transaction_provider

    def create_comments(
        self, comments: list[AgentProfileComment], conn: object | None = None
    ) -> None:
        """Create agent profile comments (batch)."""
        if conn is not None:
            self._db_adapter.write_agent_profile_comments(comments, conn=conn)
        else:
            with self._transaction_provider.run_transaction() as c:
                self._db_adapter.write_agent_profile_comments(comments, conn=c)

    def get_comments_by_agent_ids(
        self, agent_ids: Iterable[str]
    ) -> dict[str, list[AgentProfileComment]]:
        """Return comments per agent_id."""
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_agent_profile_comments_by_agent_ids(
                agent_ids, conn=c
            )


def create_sqlite_agent_profile_comment_repository(
    *,
    transaction_provider: TransactionProvider,
) -> SQLiteAgentProfileCommentRepository:
    """Factory to create SQLiteAgentProfileCommentRepository."""
    from db.adapters.sqlite import SQLiteAgentProfileCommentAdapter

    return SQLiteAgentProfileCommentRepository(
        db_adapter=SQLiteAgentProfileCommentAdapter(),
        transaction_provider=transaction_provider,
    )
