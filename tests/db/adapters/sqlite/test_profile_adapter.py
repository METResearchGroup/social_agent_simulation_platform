"""Tests for db.adapters.sqlite.profile_adapter module."""

import sqlite3
from contextlib import contextmanager
from unittest.mock import MagicMock, Mock, patch

import pytest

from db.adapters.sqlite.profile_adapter import SQLiteProfileAdapter
from simulation.core.models.profiles import BlueskyProfile


@pytest.fixture
def adapter():
    """Create a SQLiteProfileAdapter instance."""
    return SQLiteProfileAdapter()


def create_mock_row(row_data: dict) -> MagicMock:
    """Helper function to create a mock sqlite3.Row.

    Args:
        row_data: Dictionary mapping column names to values

    Returns:
        MagicMock configured to behave like a sqlite3.Row
    """
    mock_row = MagicMock()
    mock_row.__getitem__ = Mock(side_effect=lambda key: row_data[key])
    mock_row.keys = Mock(return_value=list(row_data.keys()))
    return mock_row


@pytest.fixture
def mock_db_connection():
    """Fixture that provides a context manager for mocking database connections.

    Usage:
        with mock_db_connection() as (mock_get_conn, mock_conn, mock_cursor):
            mock_cursor.fetchone.return_value = some_row
            # test code here
    """

    @contextmanager
    def _mock_db_connection():
        # Patch where it's used, not where it's defined
        with patch(
            "db.adapters.sqlite.profile_adapter.get_connection"
        ) as mock_get_conn:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.__enter__ = Mock(return_value=mock_conn)
            mock_conn.__exit__ = Mock(return_value=None)
            mock_conn.execute.return_value = mock_cursor
            mock_get_conn.return_value = mock_conn
            yield mock_get_conn, mock_conn, mock_cursor

    return _mock_db_connection


class TestSQLiteProfileAdapterWriteProfile:
    """Tests for SQLiteProfileAdapter.write_profile method."""

    def test_writes_profile_successfully(self, adapter, mock_db_connection):
        """Test that write_profile executes INSERT OR REPLACE correctly."""
        with mock_db_connection() as (mock_get_conn, mock_conn, mock_cursor):
            profile = BlueskyProfile(
                handle="test.bsky.social",
                did="did:plc:test123",
                display_name="Test User",
                bio="Test bio",
                followers_count=100,
                follows_count=50,
                posts_count=25,
            )

            adapter.write_profile(profile)

            mock_conn.execute.assert_called_once()
            call_args = mock_conn.execute.call_args
            assert "INSERT OR REPLACE INTO bluesky_profiles" in call_args[0][0]
            assert call_args[0][1] == (
                "test.bsky.social",
                "did:plc:test123",
                "Test User",
                "Test bio",
                100,
                50,
                25,
            )
            mock_conn.commit.assert_called_once()

    def test_handles_sqlite_integrity_error(self, adapter, mock_db_connection):
        """Test that IntegrityError is raised when constraints are violated."""
        with mock_db_connection() as (mock_get_conn, mock_conn, mock_cursor):
            mock_conn.execute.side_effect = sqlite3.IntegrityError(
                "Constraint violation"
            )

            profile = BlueskyProfile(
                handle="test.bsky.social",
                did="did:plc:test123",
                display_name="Test User",
                bio="Test bio",
                followers_count=100,
                follows_count=50,
                posts_count=25,
            )

            with pytest.raises(sqlite3.IntegrityError):
                adapter.write_profile(profile)


class TestSQLiteProfileAdapterReadProfile:
    """Tests for SQLiteProfileAdapter.read_profile method."""

    def test_returns_profile_when_found(self, adapter, mock_db_connection):
        """Test that read_profile returns BlueskyProfile when found."""
        with mock_db_connection() as (mock_get_conn, mock_conn, mock_cursor):
            row_data = {
                "handle": "test.bsky.social",
                "did": "did:plc:test123",
                "display_name": "Test User",
                "bio": "Test bio",
                "followers_count": 100,
                "follows_count": 50,
                "posts_count": 25,
            }
            mock_cursor.fetchone.return_value = create_mock_row(row_data)

            result = adapter.read_profile("test.bsky.social")

            assert result is not None
            assert isinstance(result, BlueskyProfile)
            assert result.handle == "test.bsky.social"
            assert result.display_name == "Test User"
            assert result.followers_count == 100

    def test_returns_none_when_not_found(self, adapter, mock_db_connection):
        """Test that read_profile returns None when profile not found."""
        with mock_db_connection() as (mock_get_conn, mock_conn, mock_cursor):
            mock_cursor.fetchone.return_value = None

            result = adapter.read_profile("nonexistent.bsky.social")

            assert result is None

    def test_raises_value_error_on_null_handle(self, adapter, mock_db_connection):
        """Test that read_profile raises ValueError when handle is NULL."""
        with mock_db_connection() as (mock_get_conn, mock_conn, mock_cursor):
            row_data = {
                "handle": None,
                "did": "did:plc:test123",
                "display_name": "Test User",
                "bio": "Test bio",
                "followers_count": 100,
                "follows_count": 50,
                "posts_count": 25,
            }
            mock_cursor.fetchone.return_value = create_mock_row(row_data)

            with pytest.raises(ValueError, match="handle cannot be NULL"):
                adapter.read_profile("test.bsky.social")

    def test_raises_value_error_on_null_did(self, adapter, mock_db_connection):
        """Test that read_profile raises ValueError when did is NULL."""
        with mock_db_connection() as (mock_get_conn, mock_conn, mock_cursor):
            row_data = {
                "handle": "test.bsky.social",
                "did": None,
                "display_name": "Test User",
                "bio": "Test bio",
                "followers_count": 100,
                "follows_count": 50,
                "posts_count": 25,
            }
            mock_cursor.fetchone.return_value = create_mock_row(row_data)

            with pytest.raises(ValueError, match="did cannot be NULL"):
                adapter.read_profile("test.bsky.social")


class TestSQLiteProfileAdapterReadAllProfiles:
    """Tests for SQLiteProfileAdapter.read_all_profiles method."""

    def test_returns_all_profiles(self, adapter, mock_db_connection):
        """Test that read_all_profiles returns list of all profiles."""
        with mock_db_connection() as (mock_get_conn, mock_conn, mock_cursor):
            row_data_1 = {
                "handle": "test1.bsky.social",
                "did": "did:plc:test1",
                "display_name": "Test User 1",
                "bio": "Bio 1",
                "followers_count": 100,
                "follows_count": 50,
                "posts_count": 25,
            }
            row_data_2 = {
                "handle": "test2.bsky.social",
                "did": "did:plc:test2",
                "display_name": "Test User 2",
                "bio": "Bio 2",
                "followers_count": 200,
                "follows_count": 75,
                "posts_count": 50,
            }
            mock_cursor.fetchall.return_value = [
                create_mock_row(row_data_1),
                create_mock_row(row_data_2),
            ]

            result = adapter.read_all_profiles()

            assert len(result) == 2
            assert result[0].handle == "test1.bsky.social"
            assert result[1].handle == "test2.bsky.social"

    def test_returns_empty_list_when_no_profiles(self, adapter, mock_db_connection):
        """Test that read_all_profiles returns empty list when no profiles exist."""
        with mock_db_connection() as (mock_get_conn, mock_conn, mock_cursor):
            mock_cursor.fetchall.return_value = []

            result = adapter.read_all_profiles()

            assert result == []
            assert isinstance(result, list)

    def test_raises_value_error_on_null_field(self, adapter, mock_db_connection):
        """Test that read_all_profiles raises ValueError when any field is NULL."""
        with mock_db_connection() as (mock_get_conn, mock_conn, mock_cursor):
            row_data = {
                "handle": "test.bsky.social",
                "did": None,  # NULL field
                "display_name": "Test User",
                "bio": "Test bio",
                "followers_count": 100,
                "follows_count": 50,
                "posts_count": 25,
            }
            mock_cursor.fetchall.return_value = [create_mock_row(row_data)]

            with pytest.raises(ValueError, match="did cannot be NULL"):
                adapter.read_all_profiles()
