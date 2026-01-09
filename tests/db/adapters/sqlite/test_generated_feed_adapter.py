"""Tests for db.adapters.sqlite.generated_feed_adapter module."""

import json
import sqlite3
from unittest.mock import Mock

import pytest

from db.adapters.sqlite.generated_feed_adapter import SQLiteGeneratedFeedAdapter
from simulation.core.models.feeds import GeneratedFeed
from tests.db.adapters.sqlite.conftest import create_mock_db_connection, create_mock_row


@pytest.fixture
def adapter():
    """Create a SQLiteGeneratedFeedAdapter instance."""
    return SQLiteGeneratedFeedAdapter()


@pytest.fixture
def default_test_data():
    """Common test data used across multiple tests."""
    return {"run_id": "run_123", "turn_number": 0, "agent_handle": "agent.bsky.social"}


@pytest.fixture
def mock_db_connection():
    """Fixture that provides a context manager for mocking database connections.

    Usage:
        with mock_db_connection() as (mock_get_conn, mock_conn, mock_cursor):
            mock_cursor.fetchall = Mock(return_value=[row1, row2])
            # test code here
    """
    return create_mock_db_connection(
        "db.adapters.sqlite.generated_feed_adapter.get_connection"
    )


class TestSQLiteGeneratedFeedAdapterReadFeedsForTurn:
    """Tests for SQLiteGeneratedFeedAdapter.read_feeds_for_turn method."""

    def test_returns_feeds_when_found(
        self, adapter, default_test_data, mock_db_connection
    ):
        """Test that read_feeds_for_turn returns list of feeds when they exist."""
        # Arrange
        run_id = default_test_data["run_id"]
        turn_number = default_test_data["turn_number"]
        agent_handle = default_test_data["agent_handle"]

        post_uris_1 = ["uri1", "uri2", "uri3"]
        post_uris_2 = ["uri4", "uri5"]

        row_data_1 = {
            "feed_id": "feed_1",
            "run_id": run_id,
            "turn_number": turn_number,
            "agent_handle": agent_handle,
            "post_uris": json.dumps(post_uris_1),
            "created_at": "2024_01_01-12:00:00",
        }
        row_data_2 = {
            "feed_id": "feed_2",
            "run_id": run_id,
            "turn_number": turn_number,
            "agent_handle": "another.agent.bsky.social",
            "post_uris": json.dumps(post_uris_2),
            "created_at": "2024_01_01-12:00:01",
        }
        mock_row_1 = create_mock_row(row_data_1)
        mock_row_2 = create_mock_row(row_data_2)

        with mock_db_connection() as (mock_get_conn, mock_conn, mock_cursor):
            mock_cursor.fetchall = Mock(return_value=[mock_row_1, mock_row_2])

            # Act
            result = adapter.read_feeds_for_turn(run_id, turn_number)

            # Assert
            assert result is not None
            assert isinstance(result, list)
            assert len(result) == 2
            assert all(isinstance(feed, GeneratedFeed) for feed in result)
            assert result[0].feed_id == "feed_1"
            assert result[0].post_uris == post_uris_1
            assert result[1].feed_id == "feed_2"
            assert result[1].post_uris == post_uris_2

            # Verify database was called with correct parameters
            mock_conn.execute.assert_called_once_with(
                "SELECT * FROM generated_feeds WHERE run_id = ? AND turn_number = ?",
                (run_id, turn_number),
            )

    def test_returns_empty_list_when_no_feeds_found(
        self, adapter, default_test_data, mock_db_connection
    ):
        """Test that read_feeds_for_turn returns empty list when no feeds exist."""
        # Arrange
        run_id = default_test_data["run_id"]
        turn_number = default_test_data["turn_number"]

        with mock_db_connection() as (mock_get_conn, mock_conn, mock_cursor):
            mock_cursor.fetchall = Mock(return_value=[])

            # Act
            result = adapter.read_feeds_for_turn(run_id, turn_number)

            # Assert
            assert result is not None
            assert isinstance(result, list)
            assert len(result) == 0

    def test_raises_operational_error_on_database_error(
        self, adapter, default_test_data, mock_db_connection
    ):
        """Test that read_feeds_for_turn raises OperationalError on database error."""
        # Arrange
        run_id = default_test_data["run_id"]
        turn_number = default_test_data["turn_number"]

        with mock_db_connection() as (mock_get_conn, mock_conn, mock_cursor):
            mock_conn.execute.side_effect = sqlite3.OperationalError("Database error")

            # Act & Assert
            with pytest.raises(sqlite3.OperationalError, match="Database error"):
                adapter.read_feeds_for_turn(run_id, turn_number)

    def test_raises_keyerror_when_missing_required_column(
        self, adapter, default_test_data, mock_db_connection
    ):
        """Test that read_feeds_for_turn raises KeyError when required column is missing."""
        # Arrange
        run_id = default_test_data["run_id"]
        turn_number = default_test_data["turn_number"]

        # Missing "feed_id" column
        row_data = {
            "run_id": run_id,
            "turn_number": turn_number,
            "agent_handle": "agent.bsky.social",
            "post_uris": json.dumps(["uri1"]),
            "created_at": "2024_01_01-12:00:00",
        }
        mock_row = create_mock_row(row_data)

        with mock_db_connection() as (mock_get_conn, mock_conn, mock_cursor):
            mock_cursor.fetchall = Mock(return_value=[mock_row])

            # Act & Assert
            with pytest.raises(KeyError):
                adapter.read_feeds_for_turn(run_id, turn_number)

    def test_raises_valueerror_when_null_fields(
        self, adapter, default_test_data, mock_db_connection
    ):
        """Test that read_feeds_for_turn raises ValueError when fields are NULL."""
        # Arrange
        run_id = default_test_data["run_id"]
        turn_number = default_test_data["turn_number"]

        # NULL feed_id
        row_data = {
            "feed_id": None,
            "run_id": run_id,
            "turn_number": turn_number,
            "agent_handle": "agent.bsky.social",
            "post_uris": json.dumps(["uri1"]),
            "created_at": "2024_01_01-12:00:00",
        }
        mock_row = create_mock_row(row_data)

        with mock_db_connection() as (mock_get_conn, mock_conn, mock_cursor):
            mock_cursor.fetchall = Mock(return_value=[mock_row])

            # Act & Assert
            with pytest.raises(ValueError, match="feed_id cannot be NULL"):
                adapter.read_feeds_for_turn(run_id, turn_number)

    def test_raises_valueerror_when_invalid_json(
        self, adapter, default_test_data, mock_db_connection
    ):
        """Test that read_feeds_for_turn raises ValueError when post_uris JSON is invalid."""
        # Arrange
        run_id = default_test_data["run_id"]
        turn_number = default_test_data["turn_number"]

        # Invalid JSON in post_uris
        row_data = {
            "feed_id": "feed_1",
            "run_id": run_id,
            "turn_number": turn_number,
            "agent_handle": "agent.bsky.social",
            "post_uris": "not valid json",
            "created_at": "2024_01_01-12:00:00",
        }
        mock_row = create_mock_row(row_data)

        with mock_db_connection() as (mock_get_conn, mock_conn, mock_cursor):
            mock_cursor.fetchall = Mock(return_value=[mock_row])

            # Act & Assert
            with pytest.raises(json.JSONDecodeError):
                adapter.read_feeds_for_turn(run_id, turn_number)

    def test_calls_database_with_correct_parameters(
        self, adapter, default_test_data, mock_db_connection
    ):
        """Test that read_feeds_for_turn calls database with correct SQL and parameters."""
        # Arrange
        run_id = default_test_data["run_id"]
        turn_number = default_test_data["turn_number"]

        with mock_db_connection() as (mock_get_conn, mock_conn, mock_cursor):
            mock_cursor.fetchall = Mock(return_value=[])

            # Act
            adapter.read_feeds_for_turn(run_id, turn_number)

            # Assert
            mock_conn.execute.assert_called_once()
            call_args = mock_conn.execute.call_args
            assert (
                call_args[0][0]
                == "SELECT * FROM generated_feeds WHERE run_id = ? AND turn_number = ?"
            )
            assert call_args[0][1] == (run_id, turn_number)
