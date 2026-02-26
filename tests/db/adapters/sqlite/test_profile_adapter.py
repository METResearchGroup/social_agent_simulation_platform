"""Tests for db.adapters.sqlite.profile_adapter module."""

import sqlite3

import pytest

from db.adapters.sqlite.profile_adapter import SQLiteProfileAdapter
from simulation.core.models.profiles import BlueskyProfile
from tests.db.adapters.sqlite.conftest import create_mock_row
from tests.factories import BlueskyProfileFactory


@pytest.fixture
def adapter():
    """Create a SQLiteProfileAdapter instance."""
    return SQLiteProfileAdapter()


class TestSQLiteProfileAdapterWriteProfile:
    """Tests for SQLiteProfileAdapter.write_profile method."""

    def test_writes_profile_successfully(self, adapter, mock_db_connection):
        """Test that write_profile executes INSERT OR REPLACE correctly."""
        with mock_db_connection() as (mock_conn, mock_cursor):
            profile = BlueskyProfileFactory.create(
                handle="test.bsky.social",
                did="did:plc:test123",
                display_name="Test User",
                bio="Test bio",
                followers_count=100,
                follows_count=50,
                posts_count=25,
            )

            adapter.write_profile(profile, conn=mock_conn)

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

    def test_handles_sqlite_integrity_error(self, adapter, mock_db_connection):
        """Test that IntegrityError is raised when constraints are violated."""
        with mock_db_connection() as (mock_conn, mock_cursor):
            mock_conn.execute.side_effect = sqlite3.IntegrityError(
                "Constraint violation"
            )

            profile = BlueskyProfileFactory.create(
                handle="test.bsky.social",
                did="did:plc:test123",
                display_name="Test User",
                bio="Test bio",
                followers_count=100,
                follows_count=50,
                posts_count=25,
            )

            with pytest.raises(sqlite3.IntegrityError):
                adapter.write_profile(profile, conn=mock_conn)


class TestSQLiteProfileAdapterReadProfile:
    """Tests for SQLiteProfileAdapter.read_profile method."""

    def test_returns_profile_when_found(self, adapter, mock_db_connection):
        """Test that read_profile returns BlueskyProfile when found."""
        with mock_db_connection() as (mock_conn, mock_cursor):
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

            result = adapter.read_profile("test.bsky.social", conn=mock_conn)

            assert result is not None
            assert isinstance(result, BlueskyProfile)
            assert result.handle == "test.bsky.social"
            assert result.display_name == "Test User"
            assert result.followers_count == 100

    def test_returns_none_when_not_found(self, adapter, mock_db_connection):
        """Test that read_profile returns None when profile not found."""
        with mock_db_connection() as (mock_conn, mock_cursor):
            mock_cursor.fetchone.return_value = None

            result = adapter.read_profile("nonexistent.bsky.social", conn=mock_conn)

            assert result is None

    @pytest.mark.parametrize(
        "null_field,expected_message",
        [("handle", "handle cannot be NULL"), ("did", "did cannot be NULL")],
    )
    def test_raises_value_error_on_null_required_field(
        self, adapter, mock_db_connection, null_field, expected_message
    ):
        """Test that read_profile raises ValueError when a required field is NULL."""
        with mock_db_connection() as (mock_conn, mock_cursor):
            row_data = {
                "handle": "test.bsky.social",
                "did": "did:plc:test123",
                "display_name": "Test User",
                "bio": "Test bio",
                "followers_count": 100,
                "follows_count": 50,
                "posts_count": 25,
            }
            row_data[null_field] = None
            mock_cursor.fetchone.return_value = create_mock_row(row_data)

            with pytest.raises(ValueError, match=expected_message):
                adapter.read_profile("test.bsky.social", conn=mock_conn)

    def test_raises_operational_error_on_database_locked(
        self, adapter, mock_db_connection
    ):
        """Test that read_profile raises OperationalError when database is locked."""
        with mock_db_connection() as (mock_conn, mock_cursor):
            mock_conn.execute.side_effect = sqlite3.OperationalError("Database locked")

            with pytest.raises(sqlite3.OperationalError, match="Database locked"):
                adapter.read_profile("test.bsky.social", conn=mock_conn)


class TestSQLiteProfileAdapterReadAllProfiles:
    """Tests for SQLiteProfileAdapter.read_all_profiles method."""

    def test_returns_all_profiles(self, adapter, mock_db_connection):
        """Test that read_all_profiles returns list of all profiles."""
        with mock_db_connection() as (mock_conn, mock_cursor):
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

            result = adapter.read_all_profiles(conn=mock_conn)

            assert len(result) == 2
            assert result[0].handle == "test1.bsky.social"
            assert result[1].handle == "test2.bsky.social"

    def test_returns_empty_list_when_no_profiles(self, adapter, mock_db_connection):
        """Test that read_all_profiles returns empty list when no profiles exist."""
        with mock_db_connection() as (mock_conn, mock_cursor):
            mock_cursor.fetchall.return_value = []

            result = adapter.read_all_profiles(conn=mock_conn)

            assert result == []
            assert isinstance(result, list)

    def test_raises_value_error_on_null_field(self, adapter, mock_db_connection):
        """Test that read_all_profiles raises ValueError when any field is NULL."""
        with mock_db_connection() as (mock_conn, mock_cursor):
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
                adapter.read_all_profiles(conn=mock_conn)

    def test_raises_operational_error_on_database_locked(
        self, adapter, mock_db_connection
    ):
        """Test that read_all_profiles raises OperationalError when database is locked."""
        with mock_db_connection() as (mock_conn, mock_cursor):
            mock_conn.execute.side_effect = sqlite3.OperationalError("Database locked")

            with pytest.raises(sqlite3.OperationalError, match="Database locked"):
                adapter.read_all_profiles(conn=mock_conn)
