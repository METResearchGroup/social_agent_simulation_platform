"""Tests for db.repositories.agent_generated_bio_repository."""

from unittest.mock import Mock

from db.adapters.base import AgentGeneratedBioDatabaseAdapter
from db.repositories.agent_generated_bio_repository import (
    SQLiteAgentGeneratedBioRepository,
)
from simulation.core.models.agent_generated_bio import AgentGeneratedBio
from simulation.core.models.generated.base import GenerationMetadata
from tests.db.repositories.conftest import make_mock_transaction_provider


def make_agent_generated_bio() -> AgentGeneratedBio:
    return AgentGeneratedBio(
        id="bio-id",
        agent_id="did:plc:test123",
        generated_bio="Generated bio text",
        metadata=GenerationMetadata(
            model_used="gpt-4o-mini",
            generation_metadata={"source": "test"},
            created_at="2026-01-01-00:00:00",
        ),
    )


class TestSQLiteAgentGeneratedBioRepository:
    def test_create_agent_generated_bio_calls_adapter(self):
        adapter = Mock(spec=AgentGeneratedBioDatabaseAdapter)
        repo = SQLiteAgentGeneratedBioRepository(
            db_adapter=adapter,
            transaction_provider=make_mock_transaction_provider(),
        )
        bio = make_agent_generated_bio()

        result = repo.create_agent_generated_bio(bio)

        assert result == bio
        adapter.write_agent_generated_bio.assert_called_once()

    def test_get_latest_agent_generated_bio_passes_through(self):
        adapter = Mock(spec=AgentGeneratedBioDatabaseAdapter)
        repo = SQLiteAgentGeneratedBioRepository(
            db_adapter=adapter,
            transaction_provider=make_mock_transaction_provider(),
        )
        bio = make_agent_generated_bio()
        adapter.read_latest_agent_generated_bio.return_value = bio

        result = repo.get_latest_agent_generated_bio("did:plc:test123")

        assert result == bio
        adapter.read_latest_agent_generated_bio.assert_called_once()

    def test_list_agent_generated_bios_passes_through(self):
        adapter = Mock(spec=AgentGeneratedBioDatabaseAdapter)
        repo = SQLiteAgentGeneratedBioRepository(
            db_adapter=adapter,
            transaction_provider=make_mock_transaction_provider(),
        )
        adapter.list_agent_generated_bios.return_value = [make_agent_generated_bio()]

        result = repo.list_agent_generated_bios("did:plc:test123")

        assert len(result) == 1
        adapter.list_agent_generated_bios.assert_called_once()

    def test_get_latest_generated_bios_by_agent_ids_passes_through(self):
        adapter = Mock(spec=AgentGeneratedBioDatabaseAdapter)
        repo = SQLiteAgentGeneratedBioRepository(
            db_adapter=adapter,
            transaction_provider=make_mock_transaction_provider(),
        )
        adapter.read_latest_agent_generated_bios_by_agent_ids.return_value = {
            "did:plc:test123": make_agent_generated_bio()
        }

        result = repo.get_latest_generated_bios_by_agent_ids(["did:plc:test123"])

        assert "did:plc:test123" in result
        adapter.read_latest_agent_generated_bios_by_agent_ids.assert_called_once()
