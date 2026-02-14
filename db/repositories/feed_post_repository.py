"""Abstraction for feed post repositories."""

from abc import ABC, abstractmethod
from typing import Iterable

from db.adapters.base import FeedPostDatabaseAdapter
from simulation.core.models.posts import BlueskyFeedPost
from simulation.core.validators import (
    validate_handle_exists, validate_posts_exist, validate_uri_exists, validate_uris_exist
)


class FeedPostRepository(ABC):
    """Abstract base class defining the interface for feed post repositories."""

    @abstractmethod
    def create_or_update_feed_post(self, post: BlueskyFeedPost) -> BlueskyFeedPost:
        """Create or update a feed post.

        Args:
            post: BlueskyFeedPost model to create or update

        Returns:
            The created or updated BlueskyFeedPost object
        """
        raise NotImplementedError

    @abstractmethod
    def create_or_update_feed_posts(
        self, posts: list[BlueskyFeedPost]
    ) -> list[BlueskyFeedPost]:
        """Create or update multiple feed posts (batch operation).

        Args:
            posts: List of BlueskyFeedPost models to create or update

        Returns:
            List of created or updated BlueskyFeedPost objects
        """
        raise NotImplementedError

    @abstractmethod
    def get_feed_post(self, uri: str) -> BlueskyFeedPost:
        """Get a feed post by URI.

        Args:
            uri: Post URI to look up

        Returns:
            BlueskyFeedPost model if found.

        Raises:
            ValueError: If uri is empty or if no feed post is found for the given URI
        """
        raise NotImplementedError

    @abstractmethod
    def list_feed_posts_by_author(self, author_handle: str) -> list[BlueskyFeedPost]:
        """List all feed posts by a specific author.

        Args:
            author_handle: Author handle to filter by

        Returns:
            List of BlueskyFeedPost models for the author.
        """
        raise NotImplementedError

    @abstractmethod
    def list_all_feed_posts(self) -> list[BlueskyFeedPost]:
        """List all feed posts.

        Returns:
            List of all BlueskyFeedPost models.
        """
        raise NotImplementedError

    @abstractmethod
    def read_feed_posts_by_uris(self, uris: Iterable[str]) -> list[BlueskyFeedPost]:
        """Read feed posts by URIs.

        Args:
            uris: Iterable of post URIs to look up

        Returns:
            List of BlueskyFeedPost models for the given URIs.
            Returns empty list if no URIs provided or if no posts found.
            Missing URIs are silently skipped (only existing posts are returned).

        Raises:
            ValueError: If the feed post data is invalid (NULL fields)
            KeyError: If required columns are missing from any database row
            Exception: Database-specific exception if the operation fails.
                      Implementations should document the specific exception types
                      they raise.
        """
        raise NotImplementedError


class SQLiteFeedPostRepository(FeedPostRepository):
    """SQLite implementation of FeedPostRepository.

    Uses dependency injection to accept a database adapter,
    decoupling it from concrete implementations.
    """

    def __init__(self, db_adapter: FeedPostDatabaseAdapter):
        """Initialize repository with injected dependencies.

        Args:
            db_adapter: Database adapter for feed post operations
        """
        self._db_adapter = db_adapter

    def create_or_update_feed_post(self, post: BlueskyFeedPost) -> BlueskyFeedPost:
        """Create or update a feed post in SQLite.

        Args:
            post: BlueskyFeedPost model to create or update

        Returns:
            The created or updated BlueskyFeedPost object

        Raises:
            ValueError: If uri is empty (validated by Pydantic model)
            sqlite3.IntegrityError: If uri violates constraints (from adapter)
            sqlite3.OperationalError: If database operation fails (from adapter)
        """
        # Validation is handled by Pydantic model (BlueskyFeedPost.validate_uri)
        self._db_adapter.write_feed_post(post)
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
            ValueError: If posts is None or if any uri is empty (validated by Pydantic models)
            sqlite3.IntegrityError: If any uri violates constraints (from adapter)
            sqlite3.OperationalError: If database operation fails (from adapter)
        """
        validate_posts_exist(posts=posts)

        # Validation is handled by Pydantic models (BlueskyFeedPost.validate_uri)
        # Pydantic will raise ValueError if any post has an empty uri
        self._db_adapter.write_feed_posts(posts)
        return posts

    def get_feed_post(self, uri: str) -> BlueskyFeedPost:
        """Get a feed post from SQLite.

        Args:
            uri: Post URI to look up

        Returns:
            BlueskyFeedPost model if found.

        Raises:
            ValueError: If uri is empty or if no feed post is found for the given URI

        Note:
            Pydantic validators only run when creating models. Since this method accepts a raw string
            parameter (not a BlueskyFeedPost model), we validate uri here.
        """
        validate_uri_exists(uri=uri)
        return self._db_adapter.read_feed_post(uri)

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
        return self._db_adapter.read_feed_posts_by_author(author_handle)

    def list_all_feed_posts(self) -> list[BlueskyFeedPost]:
        """List all feed posts from SQLite.

        Returns:
            List of all BlueskyFeedPost models.
        """
        return self._db_adapter.read_all_feed_posts()

    def read_feed_posts_by_uris(self, uris: Iterable[str]) -> list[BlueskyFeedPost]:
        """Read feed posts by URIs from SQLite.

        Args:
            uris: Iterable of post URIs to look up

        Returns:
            List of BlueskyFeedPost models for the given URIs.
            Returns empty list if no URIs provided or if no posts found.
            Missing URIs are silently skipped (only existing posts are returned).
        """
        try:
            validate_uris_exist(uris=uris)
        except ValueError:
            return []

        return self._db_adapter.read_feed_posts_by_uris(uris)


def create_sqlite_feed_post_repository() -> SQLiteFeedPostRepository:
    """Factory function to create a SQLiteFeedPostRepository with default dependencies.

    Returns:
        SQLiteFeedPostRepository configured with SQLite adapter
    """
    from db.adapters.sqlite import SQLiteFeedPostAdapter

    return SQLiteFeedPostRepository(db_adapter=SQLiteFeedPostAdapter())
