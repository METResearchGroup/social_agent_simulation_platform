"""SQLite implementation of feed post database adapter."""

import sqlite3
from typing import Iterable

from db.adapters.base import FeedPostDatabaseAdapter
from db.adapters.sqlite.schema_utils import ordered_column_names, required_column_names
from db.adapters.sqlite.sqlite import validate_required_fields
from db.schema import feed_posts
from simulation.core.models.posts import Post, PostSource
from simulation.core.utils.validators import (
    validate_handle_exists,
    validate_post_id_exists,
)

FEED_POST_COLUMNS = ordered_column_names(feed_posts)
FEED_POST_REQUIRED_FIELDS = required_column_names(feed_posts)

_INSERT_FEED_POST_SQL = (
    f"INSERT OR REPLACE INTO feed_posts ({', '.join(FEED_POST_COLUMNS)}) "
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

    def _row_to_feed_post(self, row: sqlite3.Row) -> Post:
        """Convert a database row to a Post model.

        Args:
            row: SQLite Row object containing feed post data.
                 Should be validated with _validate_feed_post_row before calling.

        Returns:
            Post model instance

        Raises:
            KeyError: If required columns are missing from row
        """
        return Post(
            post_id=row["post_id"],
            source=PostSource(row["source"]),
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

    def write_feed_post(self, post: Post, *, conn: sqlite3.Connection) -> None:
        """Write a feed post to SQLite.

        Args:
            post: Post model to write
            conn: Connection.

        Raises:
            sqlite3.IntegrityError: If uri violates constraints
            sqlite3.OperationalError: If database operation fails
        """
        values = []
        for col in FEED_POST_COLUMNS:
            if col == "source":
                values.append(post.source.value)
            else:
                values.append(getattr(post, col))
        conn.execute(_INSERT_FEED_POST_SQL, tuple(values))

    def write_feed_posts(self, posts: list[Post], *, conn: sqlite3.Connection) -> None:
        """Write multiple feed posts to SQLite (batch operation).

        Args:
            posts: List of Post models to write
            conn: Connection.

        Raises:
            sqlite3.IntegrityError: If any uri violates constraints
            sqlite3.OperationalError: If database operation fails
        """
        if not posts:
            return

        def _row(post: Post) -> tuple[object, ...]:
            row_values: list[object] = []
            for col in FEED_POST_COLUMNS:
                if col == "source":
                    row_values.append(post.source.value)
                else:
                    row_values.append(getattr(post, col))
            return tuple(row_values)

        conn.executemany(_INSERT_FEED_POST_SQL, [_row(post) for post in posts])

    def read_feed_post(self, post_id: str, *, conn: sqlite3.Connection) -> Post:
        """Read a feed post from SQLite.

        Args:
            post_id: Canonical post ID to look up
            conn: Connection.

        Returns:
            Post model if found.

        Raises:
            ValueError: If post_id is empty or if no feed post is found for the given post_id
            ValueError: If the feed post data is invalid (NULL fields)
            sqlite3.OperationalError: If database operation fails
            KeyError: If required columns are missing from the database row
        """
        validate_post_id_exists(post_id=post_id)

        row = conn.execute(
            "SELECT * FROM feed_posts WHERE post_id = ?", (post_id,)
        ).fetchone()

        if row is None:
            raise ValueError(f"No feed post found for post_id: {post_id}")

        # Validate required fields are not NULL
        context = f"feed post post_id={post_id}"
        self._validate_feed_post_row(row, context=context)

        return self._row_to_feed_post(row)

    def read_feed_posts_by_author(
        self, author_handle: str, *, conn: sqlite3.Connection
    ) -> list[Post]:
        """Read all feed posts by a specific author from SQLite.

        Args:
            author_handle: Author handle to filter by
            conn: Connection.

        Returns:
            List of Post models for the author.

        Raises:
            ValueError: If author_handle is empty
            ValueError: If any feed post data is invalid (NULL fields)
            sqlite3.OperationalError: If database operation fails
            KeyError: If required columns are missing from any database row
        """
        validate_handle_exists(author_handle)
        rows = conn.execute(
            "SELECT * FROM feed_posts WHERE author_handle = ?",
            (author_handle,),
        ).fetchall()

        posts = []
        for row in rows:
            # Validate required fields are not NULL
            # Try to get post_id for context, fallback if post_id itself is NULL
            try:
                post_id_value = (
                    row["post_id"] if row["post_id"] is not None else "unknown"
                )
                context = (
                    f"feed post post_id={post_id_value}, author_handle={author_handle}"
                )
            except (KeyError, TypeError):
                context = (
                    f"feed post (post_id unavailable), author_handle={author_handle}"
                )

            self._validate_feed_post_row(row, context=context)

            posts.append(self._row_to_feed_post(row))

        return posts

    def read_all_feed_posts(self, *, conn: sqlite3.Connection) -> list[Post]:
        """Read all feed posts from SQLite.

        Returns:
            List of Post models.

        Raises:
            ValueError: If any feed post data is invalid (NULL fields)
            sqlite3.OperationalError: If database operation fails
            KeyError: If required columns are missing from any database row
        """
        rows = conn.execute("SELECT * FROM feed_posts").fetchall()

        posts = []
        for row in rows:
            # Validate required fields are not NULL
            # Try to get post_id for context, fallback if post_id itself is NULL
            try:
                post_id_value = (
                    row["post_id"] if row["post_id"] is not None else "unknown"
                )
                context = f"feed post post_id={post_id_value}"
            except (KeyError, TypeError):
                context = "feed post (post_id unavailable)"

            self._validate_feed_post_row(row, context=context)

            posts.append(self._row_to_feed_post(row))

        return posts

    def _fetch_and_validate_rows_by_post_ids(
        self, conn: sqlite3.Connection, post_ids: Iterable[str]
    ) -> list[sqlite3.Row]:
        """Fetch rows for given post_ids, validate them, return in input order. Empty if none."""
        post_ids_list = list(post_ids)
        if not post_ids_list:
            return []
        q_marks = ",".join("?" for _ in post_ids_list)
        sql = f"SELECT * FROM feed_posts WHERE post_id IN ({q_marks})"
        result_rows = conn.execute(sql, tuple(post_ids_list)).fetchall()
        for row in result_rows:
            post_id_value = row["post_id"] if row["post_id"] is not None else "unknown"
            self._validate_feed_post_row(
                row, context=f"feed posts for post_id={post_id_value}"
            )
        row_by_post_id = {row["post_id"]: row for row in result_rows}
        return [row_by_post_id[pid] for pid in post_ids_list if pid in row_by_post_id]

    def read_feed_posts_by_ids(
        self, post_ids: Iterable[str], *, conn: sqlite3.Connection
    ) -> list[Post]:
        """Read feed posts by post_ids.

        Args:
            post_ids: Iterable of canonical post IDs to look up
            conn: Connection.

        Returns:
            List of Post models for the given post_ids.
            Returns empty list if no post_ids provided or if no posts found.
            Missing post_ids are silently skipped (only existing posts are returned).

        Raises:
            ValueError: If the feed post data is invalid (NULL fields)
            KeyError: If required columns are missing from the database row
            sqlite3.OperationalError: If database operation fails
        """
        rows = self._fetch_and_validate_rows_by_post_ids(conn, post_ids)
        return [self._row_to_feed_post(row) for row in rows]
