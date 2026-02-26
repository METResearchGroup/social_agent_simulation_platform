"""Tests for db.adapters.sqlite.generated_bio_adapter module."""

import sqlite3

import pytest

from db.adapters.sqlite.generated_bio_adapter import SQLiteGeneratedBioAdapter
from simulation.core.models.generated.bio import GeneratedBio
from tests.db.adapters.sqlite.conftest import create_mock_row
from tests.factories import GeneratedBioFactory, GenerationMetadataFactory


@pytest.fixture
def adapter():
    """Create a SQLiteGeneratedBioAdapter instance."""
    return SQLiteGeneratedBioAdapter()


class TestSQLiteGeneratedBioAdapterWriteGeneratedBio:
    """Tests for SQLiteGeneratedBioAdapter.write_generated_bio method."""

    def test_writes_bio_successfully(self, adapter, mock_db_connection):
        """Test that write_generated_bio executes INSERT OR REPLACE correctly."""
        with mock_db_connection() as (mock_conn, mock_cursor):
            bio = GeneratedBioFactory.create(
                handle="test.bsky.social",
                generated_bio="AI-generated bio text",
                metadata=GenerationMetadataFactory.create(
                    model_used=None,
                    generation_metadata=None,
                    created_at="2024_01_01-12:00:00",
                ),
            )

            adapter.write_generated_bio(bio, conn=mock_conn)

            mock_conn.execute.assert_called_once()
            call_args = mock_conn.execute.call_args
            assert "INSERT OR REPLACE INTO agent_bios" in call_args[0][0]
            assert call_args[0][1] == (
                "test.bsky.social",
                "AI-generated bio text",
                "2024_01_01-12:00:00",
            )

    def test_handles_sqlite_integrity_error(self, adapter, mock_db_connection):
        """Test that IntegrityError is raised when constraints are violated."""
        with mock_db_connection() as (mock_conn, mock_cursor):
            mock_conn.execute.side_effect = sqlite3.IntegrityError(
                "Constraint violation"
            )

            bio = GeneratedBioFactory.create(
                handle="test.bsky.social",
                generated_bio="AI-generated bio text",
                metadata=GenerationMetadataFactory.create(
                    model_used=None,
                    generation_metadata=None,
                    created_at="2024_01_01-12:00:00",
                ),
            )

            with pytest.raises(sqlite3.IntegrityError):
                adapter.write_generated_bio(bio, conn=mock_conn)


class TestSQLiteGeneratedBioAdapterReadGeneratedBio:
    """Tests for SQLiteGeneratedBioAdapter.read_generated_bio method."""

    def test_returns_bio_when_found(self, adapter, mock_db_connection):
        """Test that read_generated_bio returns GeneratedBio when found."""
        with mock_db_connection() as (mock_conn, mock_cursor):
            row_data = {
                "handle": "test.bsky.social",
                "generated_bio": "AI-generated bio text",
                "created_at": "2024_01_01-12:00:00",
            }
            mock_cursor.fetchone.return_value = create_mock_row(row_data)

            result = adapter.read_generated_bio("test.bsky.social", conn=mock_conn)

            assert result is not None
            assert isinstance(result, GeneratedBio)
            assert result.handle == "test.bsky.social"
            assert result.generated_bio == "AI-generated bio text"
            assert result.metadata.created_at == "2024_01_01-12:00:00"

    def test_returns_none_when_not_found(self, adapter, mock_db_connection):
        """Test that read_generated_bio returns None when bio not found."""
        with mock_db_connection() as (mock_conn, mock_cursor):
            mock_cursor.fetchone.return_value = None

            result = adapter.read_generated_bio(
                "nonexistent.bsky.social", conn=mock_conn
            )

            assert result is None

    def test_raises_value_error_on_null_handle(self, adapter, mock_db_connection):
        """Test that read_generated_bio raises ValueError when handle is NULL."""
        with mock_db_connection() as (mock_conn, mock_cursor):
            row_data = {
                "handle": None,
                "generated_bio": "AI-generated bio text",
                "created_at": "2024_01_01-12:00:00",
            }
            mock_cursor.fetchone.return_value = create_mock_row(row_data)

            with pytest.raises(ValueError, match="handle cannot be NULL"):
                adapter.read_generated_bio("test.bsky.social", conn=mock_conn)

    def test_raises_value_error_on_null_generated_bio(
        self, adapter, mock_db_connection
    ):
        """Test that read_generated_bio raises ValueError when generated_bio is NULL."""
        with mock_db_connection() as (mock_conn, mock_cursor):
            row_data = {
                "handle": "test.bsky.social",
                "generated_bio": None,
                "created_at": "2024_01_01-12:00:00",
            }
            mock_cursor.fetchone.return_value = create_mock_row(row_data)

            with pytest.raises(ValueError, match="generated_bio cannot be NULL"):
                adapter.read_generated_bio("test.bsky.social", conn=mock_conn)


class TestSQLiteGeneratedBioAdapterReadAllGeneratedBios:
    """Tests for SQLiteGeneratedBioAdapter.read_all_generated_bios method."""

    def test_returns_all_bios(self, adapter, mock_db_connection):
        """Test that read_all_generated_bios returns list of all bios."""
        with mock_db_connection() as (mock_conn, mock_cursor):
            row_data_1 = {
                "handle": "test1.bsky.social",
                "generated_bio": "Bio 1",
                "created_at": "2024_01_01-12:00:00",
            }
            row_data_2 = {
                "handle": "test2.bsky.social",
                "generated_bio": "Bio 2",
                "created_at": "2024_01_01-12:01:00",
            }
            mock_cursor.fetchall.return_value = [
                create_mock_row(row_data_1),
                create_mock_row(row_data_2),
            ]

            result = adapter.read_all_generated_bios(conn=mock_conn)

            assert len(result) == 2
            assert result[0].handle == "test1.bsky.social"
            assert result[1].handle == "test2.bsky.social"

    def test_returns_empty_list_when_no_bios(self, adapter, mock_db_connection):
        """Test that read_all_generated_bios returns empty list when no bios exist."""
        with mock_db_connection() as (mock_conn, mock_cursor):
            mock_cursor.fetchall.return_value = []

            result = adapter.read_all_generated_bios(conn=mock_conn)

            assert result == []
            assert isinstance(result, list)

    def test_raises_value_error_on_null_field(self, adapter, mock_db_connection):
        """Test that read_all_generated_bios raises ValueError when any field is NULL."""
        with mock_db_connection() as (mock_conn, mock_cursor):
            row_data = {
                "handle": "test.bsky.social",
                "generated_bio": None,  # NULL field
                "created_at": "2024_01_01-12:00:00",
            }
            mock_cursor.fetchall.return_value = [create_mock_row(row_data)]

            with pytest.raises(ValueError, match="generated_bio cannot be NULL"):
                adapter.read_all_generated_bios(conn=mock_conn)
