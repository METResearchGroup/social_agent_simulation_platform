"""Tests for db.adapters.sqlite.agent_generated_bio_adapter module."""

import sqlite3

import pytest

from db.adapters.sqlite.agent_generated_bio_adapter import (
    SQLiteAgentGeneratedBioAdapter,
)
from simulation.core.models.agent_generated_bio import AgentGeneratedBio
from simulation.core.models.generated.base import GenerationMetadata
from tests.db.adapters.sqlite.conftest import create_mock_row


@pytest.fixture
def adapter():
    """Create a SQLiteAgentGeneratedBioAdapter instance."""
    return SQLiteAgentGeneratedBioAdapter()


def make_agent_generated_bio(
    *,
    bio_id: str = "bio-id",
    agent_id: str = "did:plc:test123",
    generated_bio: str = "Generated bio text",
    model_used: str = "gpt-4o-mini",
) -> AgentGeneratedBio:
    metadata = GenerationMetadata(
        model_used=model_used,
        generation_metadata={"source": "test"},
        created_at="2026-01-01-00:00:00",
    )
    return AgentGeneratedBio(
        id=bio_id,
        agent_id=agent_id,
        generated_bio=generated_bio,
        metadata=metadata,
    )


class TestSQLiteAgentGeneratedBioAdapterWrite:
    def test_writes_generated_bio(self, adapter, mock_db_connection):
        with mock_db_connection() as (mock_conn, _):
            bio = make_agent_generated_bio()

            adapter.write_agent_generated_bio(bio, conn=mock_conn)

            mock_conn.execute.assert_called_once()
            sql, values = mock_conn.execute.call_args[0]
            assert "INSERT INTO agent_generated_bios" in sql
            assert values[0] == "bio-id"
            assert values[1] == "did:plc:test123"
            assert values[2] == "Generated bio text"

    def test_handles_sqlite_error(self, adapter, mock_db_connection):
        with mock_db_connection() as (mock_conn, _):
            mock_conn.execute.side_effect = sqlite3.IntegrityError("constraint")
            bio = make_agent_generated_bio()
            with pytest.raises(sqlite3.IntegrityError):
                adapter.write_agent_generated_bio(bio, conn=mock_conn)


class TestSQLiteAgentGeneratedBioAdapterRead:
    def test_returns_latest_bio(self, adapter, mock_db_connection):
        with mock_db_connection() as (mock_conn, mock_cursor):
            row_data = {
                "id": "bio-id",
                "agent_id": "did:plc:test123",
                "generated_bio": "AI bio text",
                "model_used": "gpt-test",
                "generation_metadata_json": '{"source": "test"}',
                "created_at": "2026-01-01-00:00:00",
            }
            mock_cursor.fetchone.return_value = create_mock_row(row_data)

            result = adapter.read_latest_agent_generated_bio(
                "did:plc:test123", conn=mock_conn
            )

            assert isinstance(result, AgentGeneratedBio)
            assert result.metadata.model_used == "gpt-test"
            assert result.metadata.generation_metadata is not None
            assert result.metadata.generation_metadata["source"] == "test"

    def test_returns_none_when_missing(self, adapter, mock_db_connection):
        with mock_db_connection() as (mock_conn, mock_cursor):
            mock_cursor.fetchone.return_value = None
            assert (
                adapter.read_latest_agent_generated_bio("missing", conn=mock_conn)
                is None
            )

    def test_raises_on_null_field(self, adapter, mock_db_connection):
        with mock_db_connection() as (mock_conn, mock_cursor):
            row_data = {
                "id": None,
                "agent_id": "did:plc:test123",
                "generated_bio": "AI bio text",
                "model_used": "gpt-test",
                "generation_metadata_json": None,
                "created_at": "2026-01-01-00:00:00",
            }
            mock_cursor.fetchone.return_value = create_mock_row(row_data)
            with pytest.raises(ValueError):
                adapter.read_latest_agent_generated_bio(
                    "did:plc:test123", conn=mock_conn
                )


class TestSQLiteAgentGeneratedBioAdapterList:
    def test_lists_bios(self, adapter, mock_db_connection):
        with mock_db_connection() as (mock_conn, mock_cursor):
            row_data1 = {
                "id": "bio1",
                "agent_id": "did:plc:test123",
                "generated_bio": "Bio 1",
                "model_used": None,
                "generation_metadata_json": None,
                "created_at": "2026-01-01-00:00:00",
            }
            row_data2 = {
                "id": "bio2",
                "agent_id": "did:plc:test123",
                "generated_bio": "Bio 2",
                "model_used": None,
                "generation_metadata_json": None,
                "created_at": "2026-01-01-00:00:01",
            }
            mock_cursor.fetchall.return_value = [
                create_mock_row(row_data1),
                create_mock_row(row_data2),
            ]

            result = adapter.list_agent_generated_bios(
                "did:plc:test123", conn=mock_conn
            )

            assert len(result) == 2
            assert result[0].generated_bio == "Bio 1"

    def test_latest_by_agent_ids(self, adapter, mock_db_connection):
        with mock_db_connection() as (mock_conn, mock_cursor):
            rows = [
                create_mock_row(
                    {
                        "id": "bio-a",
                        "agent_id": "aid-a",
                        "generated_bio": "A1",
                        "model_used": None,
                        "generation_metadata_json": None,
                        "created_at": "2026-01-02-00:00:00",
                    }
                ),
                create_mock_row(
                    {
                        "id": "bio-b",
                        "agent_id": "aid-b",
                        "generated_bio": "B1",
                        "model_used": None,
                        "generation_metadata_json": None,
                        "created_at": "2026-01-02-00:00:00",
                    }
                ),
            ]
            mock_cursor.fetchall.return_value = rows

            result = adapter.read_latest_agent_generated_bios_by_agent_ids(
                ["aid-a", "aid-b", "aid-c"], conn=mock_conn
            )

            assert result["aid-a"] is not None
            assert result["aid-b"] is not None
            assert result["aid-c"] is None
