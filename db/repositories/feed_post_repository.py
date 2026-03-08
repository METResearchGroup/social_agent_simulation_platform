"""SQLite implementation of feed post repositories."""

from collections.abc import Iterable

from db.adapters.base import FeedPostDatabaseAdapter, TransactionProvider
from db.repositories.interfaces import FeedPostRepository
from simulation.core.models.posts import BlueskyFeedPost
from simulation.core.utils.validators import (
    validate_handle_exists,
    validate_posts_exist,
    validate_source_id_exists,
    validate_source_ids_exist,
)


class SQLiteFeedPostRepository(FeedPostRepository):
    """SQLite implementation of FeedPostRepository.

    Uses dependency injection to accept a database adapter,
    decoupling it from concrete implementations.
    """

    def __init__(
        self,
        *,
        db_adapter: FeedPostDatabaseAdapter,
        transaction_provider: TransactionProvider,
    ):
        """Initialize repository with injected dependencies.

        Args:
            db_adapter: Database adapter for feed post operations
            transaction_provider: Provider for transactions
        """
        self._db_adapter = db_adapter
        self._transaction_provider = transaction_provider

    def create_or_update_feed_post(self, post: BlueskyFeedPost) -> BlueskyFeedPost:
        """Create or update a feed post in SQLite.

        Args:
            post: BlueskyFeedPost model to create or update

        Returns:
            The created or updated BlueskyFeedPost object

        Raises:
            ValueError: If source_id is empty (validated by Pydantic model)
            sqlite3.IntegrityError: If source_id violates constraints (from adapter)
            sqlite3.OperationalError: If database operation fails (from adapter)
        """
        # Validation is handled by Pydantic model (BlueskyFeedPost.validate_source_id)
        with self._transaction_provider.run_transaction() as c:
            self._db_adapter.write_feed_post(post, conn=c)
        return post

    def create_or_update_feed_posts(
        self, posts: list[BlueskyFeedPost]
    ) -> list[BlueskyFeedPost]:
        """Create or update multiple feed posts in SQLite (batch operation).

        Args:
            posts: List of BlueskyFeedPost models to create or update.
                   None is not allowed. Empty list is allowed and will result
                   in no database operations.

        Returns:
            List of created or updated BlueskyFeedPost objects

        Raises:
            ValueError: If posts is None or if any source_id is empty (validated by Pydantic models)
            sqlite3.IntegrityError: If any source_id violates constraints (from adapter)
            sqlite3.OperationalError: If database operation fails (from adapter)
        """
        validate_posts_exist(posts=posts)

        # Validation is handled by Pydantic models (BlueskyFeedPost.validate_source_id)
        # Pydantic will raise ValueError if any post has an empty source_id
        with self._transaction_provider.run_transaction() as c:
            self._db_adapter.write_feed_posts(posts, conn=c)
        return posts

    def get_feed_post(self, source_id: str) -> BlueskyFeedPost:
        """Get a feed post from SQLite.

        Args:
            source_id: Post source_id to look up

        Returns:
            BlueskyFeedPost model if found.

        Raises:
            ValueError: If source_id is empty or if no feed post is found for the given source_id

        Note:
            Pydantic validators only run when creating models. Since this method accepts a raw string
            parameter (not a BlueskyFeedPost model), we validate uri here.
        """
        validate_source_id_exists(source_id=source_id)
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_feed_post(source_id, conn=c)

    def list_feed_posts_by_author(self, author_handle: str) -> list[BlueskyFeedPost]:
        """List all feed posts by a specific author from SQLite.

        Args:
            author_handle: Author handle to filter by

        Returns:
            List of BlueskyFeedPost models for the author.

        Raises:
            ValueError: If author_handle is empty or None

        Note:
            Pydantic validators only run when creating models. Since this method accepts a raw string
            parameter (not a BlueskyFeedPost model), we validate author_handle here.
        """
        validate_handle_exists(handle=author_handle)
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_feed_posts_by_author(author_handle, conn=c)

    def list_all_feed_posts(self) -> list[BlueskyFeedPost]:
        """List all feed posts from SQLite.

        Returns:
            List of all BlueskyFeedPost models.
        """
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_all_feed_posts(conn=c)

    def read_feed_posts_by_source_ids(
        self, source_ids: Iterable[str]
    ) -> list[BlueskyFeedPost]:
        """Read feed posts by source_ids from SQLite.

        Args:
            source_ids: Iterable of post source_ids to look up

        Returns:
            List of BlueskyFeedPost models for the given source_ids.
            Returns empty list if no source_ids provided or if no posts found.
            Missing source_ids are silently skipped (only existing posts are returned).
        """
        try:
            validate_source_ids_exist(source_ids=source_ids)
        except ValueError:
            return []

        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_feed_posts_by_source_ids(source_ids, conn=c)


def create_sqlite_feed_post_repository(
    *,
    transaction_provider: TransactionProvider,
) -> SQLiteFeedPostRepository:
    """Factory function to create a SQLiteFeedPostRepository with default dependencies.

    Returns:
        SQLiteFeedPostRepository configured with SQLite adapter
    """
    from db.adapters.sqlite import SQLiteFeedPostAdapter

    return SQLiteFeedPostRepository(
        db_adapter=SQLiteFeedPostAdapter(),
        transaction_provider=transaction_provider,
    )
