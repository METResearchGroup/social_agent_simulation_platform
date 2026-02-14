"""SQLite implementation of feed post database adapter."""

import sqlite3
from typing import Iterable

from db.adapters.base import FeedPostDatabaseAdapter
from db.adapters.sqlite.schema_utils import ordered_column_names, required_column_names
from db.adapters.sqlite.sqlite import get_connection, validate_required_fields
from db.schema import bluesky_feed_posts
from simulation.core.models.posts import BlueskyFeedPost
from simulation.core.validators import validate_uri_exists

FEED_POST_COLUMNS = ordered_column_names(bluesky_feed_posts)
FEED_POST_REQUIRED_FIELDS = required_column_names(bluesky_feed_posts)

_INSERT_FEED_POST_SQL = (
    f"INSERT OR REPLACE INTO bluesky_feed_posts ({', '.join(FEED_POST_COLUMNS)}) "
    f"VALUES ({', '.join('?' for _ in FEED_POST_COLUMNS)})"
)


class SQLiteFeedPostAdapter(FeedPostDatabaseAdapter):
    """SQLite implementation of FeedPostDatabaseAdapter.

    This implementation raises SQLite-specific exceptions. See method docstrings
    for details on specific exception types.
    """

    def _validate_feed_post_row(
        self, row: sqlite3.Row, context: str | None = None
    ) -> None:
        """Validate that all required feed post fields are not NULL.

        Args:
            row: SQLite Row object containing feed post data
            context: Optional context string to include in error messages
                     (e.g., "feed post uri=at://did:plc:.../app.bsky.feed.post/...")

        Raises:
            ValueError: If any required field is NULL. Error message includes
                        the field name and optional context.
        """
        validate_required_fields(
            row,
            FEED_POST_REQUIRED_FIELDS,
            context=context,
        )

    def _row_to_feed_post(self, row: sqlite3.Row) -> BlueskyFeedPost:
        """Convert a database row to a BlueskyFeedPost model.

        Args:
            row: SQLite Row object containing feed post data.
                 Should be validated with _validate_feed_post_row before calling.

        Returns:
            BlueskyFeedPost model instance

        Raises:
            KeyError: If required columns are missing from row
        """
        return BlueskyFeedPost(
            id=row["uri"],
            uri=row["uri"],
            author_display_name=row["author_display_name"],
            author_handle=row["author_handle"],
            text=row["text"],
            bookmark_count=row["bookmark_count"],
            like_count=row["like_count"],
            quote_count=row["quote_count"],
            reply_count=row["reply_count"],
            repost_count=row["repost_count"],
            created_at=row["created_at"],
        )

    def write_feed_post(self, post: BlueskyFeedPost) -> None:
        """Write a feed post to SQLite.

        Args:
            post: BlueskyFeedPost model to write

        Raises:
            sqlite3.IntegrityError: If uri violates constraints
            sqlite3.OperationalError: If database operation fails
        """
        with get_connection() as conn:
            conn.execute(
                _INSERT_FEED_POST_SQL,
                tuple(getattr(post, col) for col in FEED_POST_COLUMNS),
            )
            conn.commit()

    def write_feed_posts(self, posts: list[BlueskyFeedPost]) -> None:
        """Write multiple feed posts to SQLite (batch operation).

        Args:
            posts: List of BlueskyFeedPost models to write

        Raises:
            sqlite3.IntegrityError: If any uri violates constraints
            sqlite3.OperationalError: If database operation fails
        """
        if not posts:
            return

        with get_connection() as conn:
            try:
                conn.executemany(
                    _INSERT_FEED_POST_SQL,
                    [tuple(getattr(post, col) for col in FEED_POST_COLUMNS) for post in posts],
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def read_feed_post(self, uri: str) -> BlueskyFeedPost:
        """Read a feed post from SQLite.

        Args:
            uri: Post URI to look up

        Returns:
            BlueskyFeedPost model if found.

        Raises:
            ValueError: If uri is empty or if no feed post is found for the given URI
            ValueError: If the feed post data is invalid (NULL fields)
            sqlite3.OperationalError: If database operation fails
            KeyError: If required columns are missing from the database row
        """
        validate_uri_exists(uri=uri)

        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM bluesky_feed_posts WHERE uri = ?", (uri,)
            ).fetchone()

            if row is None:
                raise ValueError(f"No feed post found for uri: {uri}")

            # Validate required fields are not NULL
            context = f"feed post uri={uri}"
            self._validate_feed_post_row(row, context=context)

            return self._row_to_feed_post(row)

    def read_feed_posts_by_author(self, author_handle: str) -> list[BlueskyFeedPost]:
        """Read all feed posts by a specific author from SQLite.

        Args:
            author_handle: Author handle to filter by

        Returns:
            List of BlueskyFeedPost models for the author.

        Raises:
            ValueError: If any feed post data is invalid (NULL fields)
            sqlite3.OperationalError: If database operation fails
            KeyError: If required columns are missing from any database row
        """
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM bluesky_feed_posts WHERE author_handle = ?",
                (author_handle,),
            ).fetchall()

            posts = []
            for row in rows:
                # Validate required fields are not NULL
                # Try to get uri for context, fallback if uri itself is NULL
                try:
                    uri_value = row["uri"] if row["uri"] is not None else "unknown"
                    context = (
                        f"feed post uri={uri_value}, author_handle={author_handle}"
                    )
                except (KeyError, TypeError):
                    context = (
                        f"feed post (uri unavailable), author_handle={author_handle}"
                    )

                self._validate_feed_post_row(row, context=context)

                posts.append(self._row_to_feed_post(row))

            return posts

    def read_all_feed_posts(self) -> list[BlueskyFeedPost]:
        """Read all feed posts from SQLite.

        Returns:
            List of BlueskyFeedPost models.

        Raises:
            ValueError: If any feed post data is invalid (NULL fields)
            sqlite3.OperationalError: If database operation fails
            KeyError: If required columns are missing from any database row
        """
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM bluesky_feed_posts").fetchall()

            posts = []
            for row in rows:
                # Validate required fields are not NULL
                # Try to get uri for context, fallback if uri itself is NULL
                try:
                    uri_value = row["uri"] if row["uri"] is not None else "unknown"
                    context = f"feed post uri={uri_value}"
                except (KeyError, TypeError):
                    context = "feed post (uri unavailable)"

                self._validate_feed_post_row(row, context=context)

                posts.append(self._row_to_feed_post(row))

            return posts

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
            KeyError: If required columns are missing from the database row
            sqlite3.OperationalError: If database operation fails
        """
        with get_connection() as conn:
            if not uris:
                rows = []
            else:
                q_marks = ",".join("?" for _ in uris)
                sql = f"SELECT * FROM bluesky_feed_posts WHERE uri IN ({q_marks})"
                result_rows = conn.execute(sql, tuple(uris)).fetchall()
                # Validate all returned rows before filtering (catches data integrity issues)
                for row in result_rows:
                    uri_value = row["uri"] if row["uri"] is not None else "unknown"
                    context = f"feed posts for uri={uri_value}"
                    self._validate_feed_post_row(row, context=context)
                # Re-map rows by uri and restore input order
                row_by_uri = {row["uri"]: row for row in result_rows}
                rows = [row_by_uri[uri] for uri in uris if uri in row_by_uri]

            if len(rows) == 0:
                return []

            posts = []
            for row in rows:
                posts.append(self._row_to_feed_post(row))

            return posts
