"""SQLite implementation of generated feed database adapter."""

import json
import sqlite3

from db.adapters.base import GeneratedFeedDatabaseAdapter
from db.adapters.sqlite.schema_utils import ordered_column_names, required_column_names
from db.adapters.sqlite.sqlite import get_connection, validate_required_fields
from db.schema import generated_feeds
from simulation.core.models.feeds import GeneratedFeed
from simulation.core.validators import (
    validate_handle_exists,
    validate_run_id,
    validate_turn_number,
)

GENERATED_FEED_COLUMNS = ordered_column_names(generated_feeds)
GENERATED_FEED_REQUIRED_FIELDS = required_column_names(generated_feeds)
_INSERT_GENERATED_FEED_SQL = (
    f"INSERT OR REPLACE INTO generated_feeds ({', '.join(GENERATED_FEED_COLUMNS)}) "
    f"VALUES ({', '.join('?' for _ in GENERATED_FEED_COLUMNS)})"
)


class SQLiteGeneratedFeedAdapter(GeneratedFeedDatabaseAdapter):
    """SQLite implementation of GeneratedFeedDatabaseAdapter.

    This implementation raises SQLite-specific exceptions. See method docstrings
    for details on specific exception types.
    """

    def _validate_generated_feed_row(
        self, row: sqlite3.Row, context: str | None = None
    ) -> None:
        """Validate that all required generated feed fields are not NULL.

        Args:
            row: SQLite Row object containing generated feed data
            context: Optional context string to include in error messages
                     (e.g., "generated feed agent_handle=user.bsky.social, run_id=...")

        Raises:
            ValueError: If any required field is NULL. Error message includes
                        the field name and optional context.
        """
        validate_required_fields(
            row,
            GENERATED_FEED_REQUIRED_FIELDS,
            context=context,
        )

    def write_generated_feed(self, feed: GeneratedFeed) -> None:
        """Write a generated feed to SQLite.

        Args:
            feed: GeneratedFeed model to write

        Raises:
            sqlite3.IntegrityError: If composite key violates constraints
            sqlite3.OperationalError: If database operation fails
        """
        row_values = tuple(
            json.dumps(feed.post_uris) if col == "post_uris" else getattr(feed, col)
            for col in GENERATED_FEED_COLUMNS
        )
        with get_connection() as conn:
            conn.execute(_INSERT_GENERATED_FEED_SQL, row_values)
            conn.commit()

    def read_generated_feed(
        self, agent_handle: str, run_id: str, turn_number: int
    ) -> GeneratedFeed:
        """Read a generated feed from SQLite.

        Args:
            agent_handle: Agent handle to look up
            run_id: Run ID to look up
            turn_number: Turn number to look up

        Returns:
            GeneratedFeed model for the specified agent, run, and turn.

        Raises:
            ValueError: If no feed is found for the given composite key
            ValueError: If the feed data is invalid (NULL fields)
            sqlite3.OperationalError: If database operation fails
            KeyError: If required columns are missing from the database row
        """
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM generated_feeds WHERE agent_handle = ? AND run_id = ? AND turn_number = ?",
                (agent_handle, run_id, turn_number),
            ).fetchone()

            if row is None:
                # this isn't supposed to happen, so we want to raise an error if it does.
                raise ValueError(
                    f"Generated feed not found for agent {agent_handle}, run {run_id}, turn {turn_number}"
                )

            context = f"generated feed agent_handle={agent_handle}, run_id={run_id}, turn_number={turn_number}"
            self._validate_generated_feed_row(row, context=context)
            return self._row_to_generated_feed(row)

    def _row_to_generated_feed(self, row: sqlite3.Row) -> GeneratedFeed:
        """Build GeneratedFeed from a validated row. Call _validate_generated_feed_row first."""
        return GeneratedFeed(
            feed_id=row["feed_id"],
            run_id=row["run_id"],
            turn_number=row["turn_number"],
            agent_handle=row["agent_handle"],
            post_uris=json.loads(row["post_uris"]),
            created_at=row["created_at"],
        )

    def _context_for_generated_feed_row(self, row: sqlite3.Row) -> str:
        """Build context string for validation error messages."""
        try:
            ah = row["agent_handle"] if row["agent_handle"] is not None else "unknown"
            rid = row["run_id"] if row["run_id"] is not None else "unknown"
            tn = row["turn_number"] if row["turn_number"] is not None else "unknown"
            return f"generated feed agent_handle={ah}, run_id={rid}, turn_number={tn}"
        except (KeyError, TypeError):
            return "generated feed (identifying info unavailable)"

    def read_all_generated_feeds(self) -> list[GeneratedFeed]:
        """Read all generated feeds from SQLite.

        Returns:
            List of GeneratedFeed models.

        Raises:
            ValueError: If any feed data is invalid (NULL fields)
            sqlite3.OperationalError: If database operation fails
            KeyError: If required columns are missing from any database row
        """
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM generated_feeds").fetchall()
        feeds = []
        for row in rows:
            self._validate_generated_feed_row(
                row, context=self._context_for_generated_feed_row(row)
            )
            feeds.append(self._row_to_generated_feed(row))
        return feeds

    def read_post_uris_for_run(self, agent_handle: str, run_id: str) -> set[str]:
        """Read all post URIs from generated feeds for a specific agent and run.

        Args:
            agent_handle: Agent handle to filter by
            run_id: Run ID to filter by

        Returns:
            Set of post URIs from all generated feeds matching the agent and run.
            Returns empty set if no feeds found.

        Raises:
            ValueError: If agent_handle or run_id is empty
            sqlite3.OperationalError: If database operation fails
        """
        validate_handle_exists(agent_handle)
        validate_run_id(run_id)

        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT post_uris
                FROM generated_feeds
                WHERE agent_handle = ? AND run_id = ?
            """,
                (agent_handle, run_id),
            ).fetchall()
            return {uri for row in rows for uri in json.loads(row["post_uris"])}

    def read_feeds_for_turn(self, run_id: str, turn_number: int) -> list[GeneratedFeed]:
        """Read all generated feeds for a specific run and turn.

        Args:
            run_id: The ID of the run
            turn_number: The turn number (0-indexed)

        Returns:
            List of GeneratedFeed models for the specified run and turn.
            Returns empty list if no feeds found.

        Raises:
            ValueError: If run_id or turn_number is invalid
            ValueError: If the feed data is invalid (NULL fields, invalid JSON)
            KeyError: If required columns are missing from the database row
            sqlite3.OperationalError: If database operation fails
        """
        validate_run_id(run_id)
        validate_turn_number(turn_number)
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM generated_feeds WHERE run_id = ? AND turn_number = ?",
                (run_id, turn_number),
            ).fetchall()

            if len(rows) == 0:
                return []

            context = f"generated feed for run {run_id}, turn {turn_number}"
            feeds = []
            for row in rows:
                self._validate_generated_feed_row(row, context=context)
                feeds.append(self._row_to_generated_feed(row))
            return feeds
