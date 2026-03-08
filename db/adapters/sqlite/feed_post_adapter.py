"""SQLite implementation of feed post database adapter."""

import sqlite3
from typing import Iterable

from db.adapters.base import FeedPostDatabaseAdapter
from db.adapters.sqlite.schema_utils import ordered_column_names, required_column_names
from db.adapters.sqlite.sqlite import validate_required_fields
from db.schema import bluesky_feed_posts
from simulation.core.models.posts import BlueskyFeedPost
from simulation.core.utils.validators import (
    validate_handle_exists,
    validate_source_id_exists,
)

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
                     (e.g., "feed post source_id=at://did:plc:.../app.bsky.feed.post/...")

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
            id=row["source_id"],
            source_id=row["source_id"],
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

    def write_feed_post(
        self, post: BlueskyFeedPost, *, conn: sqlite3.Connection
    ) -> None:
        """Write a feed post to SQLite.

        Args:
            post: BlueskyFeedPost model to write
            conn: Connection.

        Raises:
            sqlite3.IntegrityError: If source_id violates constraints
            sqlite3.OperationalError: If database operation fails
        """
        conn.execute(
            _INSERT_FEED_POST_SQL,
            tuple(getattr(post, col) for col in FEED_POST_COLUMNS),
        )

    def write_feed_posts(
        self, posts: list[BlueskyFeedPost], *, conn: sqlite3.Connection
    ) -> None:
        """Write multiple feed posts to SQLite (batch operation).

        Args:
            posts: List of BlueskyFeedPost models to write
            conn: Connection.

        Raises:
            sqlite3.IntegrityError: If any source_id violates constraints
            sqlite3.OperationalError: If database operation fails
        """
        if not posts:
            return

        conn.executemany(
            _INSERT_FEED_POST_SQL,
            [tuple(getattr(post, col) for col in FEED_POST_COLUMNS) for post in posts],
        )

    def read_feed_post(
        self, source_id: str, *, conn: sqlite3.Connection
    ) -> BlueskyFeedPost:
        """Read a feed post from SQLite.

        Args:
            source_id: Post source_id to look up
            conn: Connection.

        Returns:
            BlueskyFeedPost model if found.

        Raises:
            ValueError: If source_id is empty or if no feed post is found for the given source_id
            ValueError: If the feed post data is invalid (NULL fields)
            sqlite3.OperationalError: If database operation fails
            KeyError: If required columns are missing from the database row
        """
        validate_source_id_exists(source_id=source_id)

        row = conn.execute(
            "SELECT * FROM bluesky_feed_posts WHERE source_id = ?", (source_id,)
        ).fetchone()

        if row is None:
            raise ValueError(f"No feed post found for source_id: {source_id}")

        # Validate required fields are not NULL
        context = f"feed post source_id={source_id}"
        self._validate_feed_post_row(row, context=context)

        return self._row_to_feed_post(row)

    def read_feed_posts_by_author(
        self, author_handle: str, *, conn: sqlite3.Connection
    ) -> list[BlueskyFeedPost]:
        """Read all feed posts by a specific author from SQLite.

        Args:
            author_handle: Author handle to filter by
            conn: Connection.

        Returns:
            List of BlueskyFeedPost models for the author.

        Raises:
            ValueError: If author_handle is empty
            ValueError: If any feed post data is invalid (NULL fields)
            sqlite3.OperationalError: If database operation fails
            KeyError: If required columns are missing from any database row
        """
        validate_handle_exists(author_handle)
        rows = conn.execute(
            "SELECT * FROM bluesky_feed_posts WHERE author_handle = ?",
            (author_handle,),
        ).fetchall()

        posts = []
        for row in rows:
            # Validate required fields are not NULL
            # Try to get source_id for context, fallback if source_id itself is NULL
            try:
                source_id_value = (
                    row["source_id"] if row["source_id"] is not None else "unknown"
                )
                context = f"feed post source_id={source_id_value}, author_handle={author_handle}"
            except (KeyError, TypeError):
                context = (
                    f"feed post (source_id unavailable), author_handle={author_handle}"
                )

            self._validate_feed_post_row(row, context=context)

            posts.append(self._row_to_feed_post(row))

        return posts

    def read_all_feed_posts(self, *, conn: sqlite3.Connection) -> list[BlueskyFeedPost]:
        """Read all feed posts from SQLite.

        Returns:
            List of BlueskyFeedPost models.

        Raises:
            ValueError: If any feed post data is invalid (NULL fields)
            sqlite3.OperationalError: If database operation fails
            KeyError: If required columns are missing from any database row
        """
        rows = conn.execute("SELECT * FROM bluesky_feed_posts").fetchall()

        posts = []
        for row in rows:
            # Validate required fields are not NULL
            # Try to get source_id for context, fallback if source_id itself is NULL
            try:
                source_id_value = (
                    row["source_id"] if row["source_id"] is not None else "unknown"
                )
                context = f"feed post source_id={source_id_value}"
            except (KeyError, TypeError):
                context = "feed post (source_id unavailable)"

            self._validate_feed_post_row(row, context=context)

            posts.append(self._row_to_feed_post(row))

        return posts

    def _fetch_and_validate_rows_by_source_ids(
        self, conn: sqlite3.Connection, source_ids: Iterable[str]
    ) -> list[sqlite3.Row]:
        """Fetch rows for given source_ids, validate them, return in input order. Empty if none."""
        source_ids_list = list(source_ids)
        if not source_ids_list:
            return []
        q_marks = ",".join("?" for _ in source_ids_list)
        sql = f"SELECT * FROM bluesky_feed_posts WHERE source_id IN ({q_marks})"
        result_rows = conn.execute(sql, tuple(source_ids_list)).fetchall()
        for row in result_rows:
            source_id_value = (
                row["source_id"] if row["source_id"] is not None else "unknown"
            )
            self._validate_feed_post_row(
                row, context=f"feed posts for source_id={source_id_value}"
            )
        row_by_source_id = {row["source_id"]: row for row in result_rows}
        return [
            row_by_source_id[source_id]
            for source_id in source_ids_list
            if source_id in row_by_source_id
        ]

    def read_feed_posts_by_source_ids(
        self, source_ids: Iterable[str], *, conn: sqlite3.Connection
    ) -> list[BlueskyFeedPost]:
        """Read feed posts by source_ids.

        Args:
            source_ids: Iterable of post source_ids to look up
            conn: Connection.

        Returns:
            List of BlueskyFeedPost models for the given source_ids.
            Returns empty list if no source_ids provided or if no posts found.
            Missing source_ids are silently skipped (only existing posts are returned).

        Raises:
            ValueError: If the feed post data is invalid (NULL fields)
            KeyError: If required columns are missing from the database row
            sqlite3.OperationalError: If database operation fails
        """
        rows = self._fetch_and_validate_rows_by_source_ids(conn, source_ids)
        return [self._row_to_feed_post(row) for row in rows]
