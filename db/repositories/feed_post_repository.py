"""SQLite implementation of feed post repositories."""

from collections.abc import Iterable

from db.adapters.base import FeedPostDatabaseAdapter, TransactionProvider
from db.repositories.interfaces import FeedPostRepository
from simulation.core.models.posts import Post
from simulation.core.utils.validators import (
    validate_handle_exists,
    validate_post_id_exists,
    validate_post_ids_exist,
    validate_posts_exist,
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

    def create_or_update_feed_post(self, post: Post) -> Post:
        """Create or update a feed post in SQLite.

        Args:
            post: Post model to create or update

        Returns:
            The created or updated Post object

        Raises:
            ValueError: If post_id is empty (validated by Pydantic model)
            sqlite3.IntegrityError: If post_id violates constraints (from adapter)
            sqlite3.OperationalError: If database operation fails (from adapter)
        """
        # Validation is handled by Pydantic model validators.
        with self._transaction_provider.run_transaction() as c:
            self._db_adapter.write_feed_post(post, conn=c)
        return post

    def create_or_update_feed_posts(self, posts: list[Post]) -> list[Post]:
        """Create or update multiple feed posts in SQLite (batch operation).

        Args:
            posts: List of Post models to create or update.
                   None is not allowed. Empty list is allowed and will result
                   in no database operations.

        Returns:
            List of created or updated Post objects

        Raises:
            ValueError: If posts is None or if any post_id is empty (validated by Pydantic models)
            sqlite3.IntegrityError: If any post_id violates constraints (from adapter)
            sqlite3.OperationalError: If database operation fails (from adapter)
        """
        validate_posts_exist(posts=posts)

        # Validation is handled by Pydantic models.
        with self._transaction_provider.run_transaction() as c:
            self._db_adapter.write_feed_posts(posts, conn=c)
        return posts

    def get_feed_post(self, post_id: str) -> Post:
        """Get a feed post from SQLite.

        Args:
            post_id: Canonical post ID to look up

        Returns:
            Post model if found.

        Raises:
            ValueError: If post_id is empty or if no feed post is found for the given post_id

        Note:
            Pydantic validators only run when creating models. Since this method accepts a raw string
            parameter (not a Post model), we validate post_id here.
        """
        validate_post_id_exists(post_id=post_id)
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_feed_post(post_id, conn=c)

    def list_feed_posts_by_author(self, author_handle: str) -> list[Post]:
        """List all feed posts by a specific author from SQLite.

        Args:
            author_handle: Author handle to filter by

        Returns:
            List of Post models for the author.

        Raises:
            ValueError: If author_handle is empty or None

        Note:
            Pydantic validators only run when creating models. Since this method accepts a raw string
            parameter (not a Post model), we validate author_handle here.
        """
        validate_handle_exists(handle=author_handle)
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_feed_posts_by_author(author_handle, conn=c)

    def list_all_feed_posts(self) -> list[Post]:
        """List all feed posts from SQLite.

        Returns:
            List of all Post models.
        """
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_all_feed_posts(conn=c)

    def read_feed_posts_by_ids(self, post_ids: Iterable[str]) -> list[Post]:
        """Read feed posts by canonical post_ids from SQLite.

        Args:
            post_ids: Iterable of post_ids to look up

        Returns:
            List of Post models for the given post_ids.
            Returns empty list if no post_ids provided or if no posts found.
            Missing post_ids are silently skipped (only existing posts are returned).
        """
        try:
            validate_post_ids_exist(post_ids=post_ids)
        except ValueError:
            return []

        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_feed_posts_by_ids(post_ids, conn=c)


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
