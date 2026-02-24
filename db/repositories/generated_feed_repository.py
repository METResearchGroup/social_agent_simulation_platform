"""SQLite implementation of generated feed repositories."""

from db.adapters.base import GeneratedFeedDatabaseAdapter, TransactionProvider
from db.repositories.interfaces import GeneratedFeedRepository
from lib.validation_decorators import validate_inputs
from simulation.core.models.feeds import GeneratedFeed
from simulation.core.validators import (
    validate_handle_exists,
    validate_run_id,
    validate_turn_number,
)


class SQLiteGeneratedFeedRepository(GeneratedFeedRepository):
    """SQLite implementation of GeneratedFeedRepository.

    Uses dependency injection to accept a database adapter,
    decoupling it from concrete implementations.
    """

    def __init__(
        self,
        *,
        db_adapter: GeneratedFeedDatabaseAdapter,
        transaction_provider: TransactionProvider,
    ):
        """Initialize repository with injected dependencies.

        Args:
            db_adapter: Database adapter for generated feed operations
            transaction_provider: Provider for transactions
        """
        self._db_adapter = db_adapter
        self._transaction_provider = transaction_provider

    def write_generated_feed(self, feed: GeneratedFeed) -> GeneratedFeed:
        """Write a generated feed to SQLite (insert or replace by composite key).

        Args:
            feed: GeneratedFeed model to create or update

        Returns:
            The created or updated GeneratedFeed object

        Raises:
            ValueError: If agent_handle or run_id is empty (validated by Pydantic model)
            sqlite3.IntegrityError: If composite key violates constraints (from adapter)
            sqlite3.OperationalError: If database operation fails (from adapter)

        Note:
            This write is idempotent: an existing row with the same composite
            key (agent_handle, run_id, turn_number) may be replaced. Callers can
            safely retry or recompute; duplicate writes do not raise. The adapter
            uses INSERT OR REPLACE (delete+insert semantics).
            turn_number is validated by Pydantic at model creation time, so it cannot be None.
            agent_handle and run_id are validated by Pydantic field validators.
        """
        # Validation is handled by Pydantic model (GeneratedFeed.validate_agent_handle, validate_run_id)
        with self._transaction_provider.run_transaction() as c:
            self._db_adapter.write_generated_feed(feed, conn=c)
        return feed

    @validate_inputs(
        (validate_handle_exists, "agent_handle"),
        (validate_run_id, "run_id"),
        (validate_turn_number, "turn_number"),
    )
    def get_generated_feed(
        self, agent_handle: str, run_id: str, turn_number: int
    ) -> GeneratedFeed:
        """Get a generated feed from SQLite.

        Args:
            agent_handle: Agent handle to look up
            run_id: Run ID to look up
            turn_number: Turn number to look up

        Returns:
            GeneratedFeed model for the specified agent, run, and turn.

        Raises:
            ValueError: If agent_handle or run_id is empty
            ValueError: If no feed is found for the given composite key (from adapter)

        Note:
            turn_number is validated by the function signature (int type), so it cannot be None.
            Pydantic validators only run when creating models. Since this method accepts raw string
            parameters (not a GeneratedFeed model), we validate agent_handle and run_id here.
        """
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_generated_feed(
                agent_handle, run_id, turn_number, conn=c
            )

    def list_all_generated_feeds(self) -> list[GeneratedFeed]:
        """List all generated feeds from SQLite.

        Returns:
            List of all GeneratedFeed models.
        """
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_all_generated_feeds(conn=c)

    @validate_inputs(
        (validate_handle_exists, "agent_handle"), (validate_run_id, "run_id")
    )
    def get_post_uris_for_run(self, agent_handle: str, run_id: str) -> set[str]:
        """Get all post URIs from generated feeds for a specific agent and run.

        Args:
            agent_handle: Agent handle to filter by
            run_id: Run ID to filter by

        Returns:
            Set of post URIs from all generated feeds matching the agent and run.
            Returns empty set if no feeds found.

        Raises:
            ValueError: If agent_handle or run_id is empty

        Note:
            Pydantic validators only run when creating models. Since this method accepts raw string
            parameters (not a GeneratedFeed model), we validate agent_handle and run_id here.
        """
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_post_uris_for_run(agent_handle, run_id, conn=c)

    @validate_inputs((validate_run_id, "run_id"), (validate_turn_number, "turn_number"))
    def read_feeds_for_turn(self, run_id: str, turn_number: int) -> list[GeneratedFeed]:
        """Read all generated feeds for a specific run and turn.

        Args:
            run_id: The ID of the run
            turn_number: The turn number (0-indexed)

        Returns:
            List of GeneratedFeed models for the specified run and turn.
            Returns empty list if no feeds found.

        Raises:
            ValueError: If the feed data is invalid (NULL fields)
            KeyError: If required columns are missing from the database row
            Exception: Database-specific exception if the operation fails.
                      Implementations should document the specific exception types
                      they raise.
        """
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_feeds_for_turn(run_id, turn_number, conn=c)


def create_sqlite_generated_feed_repository(
    *,
    transaction_provider: TransactionProvider,
) -> SQLiteGeneratedFeedRepository:
    """Factory function to create a SQLiteGeneratedFeedRepository with default dependencies.

    Returns:
        SQLiteGeneratedFeedRepository configured with SQLite adapter
    """
    from db.adapters.sqlite import SQLiteGeneratedFeedAdapter

    return SQLiteGeneratedFeedRepository(
        db_adapter=SQLiteGeneratedFeedAdapter(),
        transaction_provider=transaction_provider,
    )
