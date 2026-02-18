"""Tests for db.adapters.sqlite.sqlite module."""

import os
import sqlite3
import tempfile
from unittest.mock import patch

import pytest

from db.adapters.sqlite.schema_utils import ordered_column_names, required_column_names
from db.adapters.sqlite.sqlite import (
    DB_PATH,
    get_connection,
    get_db_path,
    initialize_database,
)
from db.schema import bluesky_feed_posts


@pytest.fixture
def temp_db():
    """Fixture that creates a temporary database file.

    Yields the temporary database path. On teardown, deletes the temporary file.
    """
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
        temp_db_path = tmp.name

    try:
        yield temp_db_path
    finally:
        if os.path.exists(temp_db_path):
            os.unlink(temp_db_path)


class TestDBPath:
    """Tests for DB_PATH constant."""

    def test_db_path_is_absolute(self):
        """Test that DB_PATH is an absolute path."""
        assert os.path.isabs(DB_PATH)

    def test_db_path_ends_with_db_sqlite(self):
        """Test that DB_PATH ends with db.sqlite."""
        assert DB_PATH.endswith("db.sqlite")

    def test_get_db_path_uses_default_when_env_not_set(self):
        """get_db_path returns DB_PATH when SIM_DB_PATH is unset."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SIM_DB_PATH", None)
            expected_result = DB_PATH
            assert get_db_path() == expected_result

    def test_get_db_path_uses_env_override(self, temp_db):
        """get_db_path prefers SIM_DB_PATH when provided."""
        with patch.dict(os.environ, {"SIM_DB_PATH": temp_db}, clear=False):
            expected_result = temp_db
            assert get_db_path() == expected_result


class TestGetConnection:
    """Tests for get_connection function."""

    def test_returns_sqlite_connection(self):
        """Test that get_connection returns a sqlite3.Connection."""
        conn = get_connection()
        assert isinstance(conn, sqlite3.Connection)
        conn.close()

    def test_connection_has_row_factory(self):
        """Test that connection has row_factory set to sqlite3.Row."""
        conn = get_connection()
        assert conn.row_factory == sqlite3.Row
        conn.close()

    def test_connection_connects_to_correct_database(self):
        """Test that connection connects to the database specified by DB_PATH."""
        conn = get_connection()
        # Verify we can query the database
        cursor = conn.execute("SELECT 1")
        assert cursor.fetchone()[0] == 1
        conn.close()

    def test_connection_uses_sim_db_path_env_override(self, temp_db):
        """get_connection should connect to path provided by SIM_DB_PATH."""
        with patch.dict(os.environ, {"SIM_DB_PATH": temp_db}, clear=False):
            conn = get_connection()
            cursor = conn.execute("PRAGMA database_list")
            rows = cursor.fetchall()
            conn.close()

        # Row format: (seq, name, file); row 0 is "main".
        connected_path = rows[0][2]
        expected_result = os.path.realpath(temp_db)
        assert os.path.realpath(connected_path) == expected_result


class TestInitializeDatabase:
    """Tests for initialize_database function."""

    def test_creates_all_tables(self, temp_db):
        """Test that initialize_database creates all required tables."""
        with patch("db.adapters.sqlite.sqlite.DB_PATH", temp_db):
            # Initialize database
            initialize_database()

            # Verify tables exist by querying them
            conn = get_connection()
            tables = [
                "bluesky_profiles",
                "bluesky_feed_posts",
                "agent_bios",
                "generated_feeds",
                "runs",
                "turn_metadata",
                "turn_metrics",
                "run_metrics",
            ]

            for table in tables:
                cursor = conn.execute(
                    f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"
                )
                result = cursor.fetchone()
                assert result is not None, f"Table {table} was not created"

            conn.close()

    def test_creates_indexes(self, temp_db):
        """Test that initialize_database creates required indexes."""
        with patch("db.adapters.sqlite.sqlite.DB_PATH", temp_db):
            # Initialize database
            initialize_database()

            # Verify indexes exist
            conn = get_connection()
            indexes = [
                "idx_runs_status",
                "idx_runs_created_at",
                "idx_bluesky_feed_posts_author_handle",
                "idx_turn_metadata_run_id",
                "idx_turn_metrics_run_id",
            ]

            for index in indexes:
                cursor = conn.execute(
                    f"SELECT name FROM sqlite_master WHERE type='index' AND name='{index}'"
                )
                result = cursor.fetchone()
                assert result is not None, f"Index {index} was not created"

            conn.close()

    def test_idempotent(self, temp_db):
        """Test that initialize_database can be called multiple times safely."""
        with patch("db.adapters.sqlite.sqlite.DB_PATH", temp_db):
            # Initialize database multiple times
            initialize_database()
            initialize_database()
            initialize_database()

            # Verify tables still exist
            conn = get_connection()
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='runs'"
            )
            result = cursor.fetchone()
            assert result is not None
            conn.close()

    def test_creates_tables_with_correct_schema(self, temp_db):
        """Test that initialize_database creates tables with correct schema."""
        with patch("db.adapters.sqlite.sqlite.DB_PATH", temp_db):
            # Initialize database
            initialize_database()

            # Verify runs table has correct columns
            conn = get_connection()
            cursor = conn.execute("PRAGMA table_info(runs)")
            columns = {row[1]: row[2] for row in cursor.fetchall()}

            expected_columns = {
                "run_id": "TEXT",
                "created_at": "TEXT",
                "total_turns": "INTEGER",
                "total_agents": "INTEGER",
                "feed_algorithm": "TEXT",
                "started_at": "TEXT",
                "status": "TEXT",
                "completed_at": "TEXT",
            }

            for col_name, col_type in expected_columns.items():
                assert col_name in columns, f"Column {col_name} not found"
                assert columns[col_name] == col_type, (
                    f"Column {col_name} has wrong type: {columns[col_name]}"
                )

            conn.close()

    def test_bluesky_feed_posts_schema_matches_canonical(self, temp_db):
        """PRAGMA table_info(bluesky_feed_posts) matches db.schema column order and NOT NULL."""
        with patch("db.adapters.sqlite.sqlite.DB_PATH", temp_db):
            initialize_database()

            conn = get_connection()
            cursor = conn.execute("PRAGMA table_info(bluesky_feed_posts)")
            rows = cursor.fetchall()
            conn.close()

            # PRAGMA table_info: (cid, name, type, notnull, dflt_value, pk)
            db_columns = [row[1] for row in rows]
            db_notnull = {row[1]: bool(row[3]) for row in rows}

            expected_order = ordered_column_names(bluesky_feed_posts)
            assert db_columns == expected_order, (
                f"bluesky_feed_posts column order mismatch: got {db_columns}, expected {expected_order}"
            )

            required = set(required_column_names(bluesky_feed_posts))
            for col in expected_order:
                assert db_notnull[col] == (col in required), (
                    f"bluesky_feed_posts.{col}: NOT NULL in DB is {db_notnull[col]}, "
                    f"schema nullable=False is {col in required}"
                )
