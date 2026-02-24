"""Integration tests for db.repositories.agent_bio_repository module."""

import os
import tempfile

import pytest

from db.adapters.sqlite.sqlite import (
    DB_PATH,
    SqliteTransactionProvider,
    initialize_database,
)
from db.repositories.agent_bio_repository import create_sqlite_agent_bio_repository
from db.repositories.agent_repository import create_sqlite_agent_repository
from simulation.core.models.agent import Agent, PersonaSource
from simulation.core.models.agent_bio import AgentBio, PersonaBioSource


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    import db.adapters.sqlite.sqlite as sqlite_module

    original_path = DB_PATH
    fd, temp_path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    sqlite_module.DB_PATH = temp_path
    initialize_database()
    yield temp_path
    sqlite_module.DB_PATH = original_path
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def agent_in_db(temp_db):
    """Create an agent in the database for bio tests."""
    agent_repo = create_sqlite_agent_repository(
        transaction_provider=SqliteTransactionProvider()
    )
    agent = Agent(
        agent_id="did:plc:test123",
        handle="test.bsky.social",
        persona_source=PersonaSource.SYNC_BLUESKY,
        display_name="Test User",
        created_at="2026_02_19-10:00:00",
        updated_at="2026_02_19-10:00:00",
    )
    agent_repo.create_or_update_agent(agent)
    return "did:plc:test123"


class TestSQLiteAgentBioRepositoryIntegration:
    """Integration tests for AgentBioRepository using a real database."""

    def test_create_and_get_latest_bio(self, temp_db, agent_in_db):
        """Test creating a bio and retrieving it as latest."""
        repo = create_sqlite_agent_bio_repository(
            transaction_provider=SqliteTransactionProvider()
        )
        bio = AgentBio(
            id="bio1",
            agent_id=agent_in_db,
            persona_bio="AI-generated persona bio.",
            persona_bio_source=PersonaBioSource.AI_GENERATED,
            created_at="2026_02_19-10:00:00",
            updated_at="2026_02_19-10:00:00",
        )
        repo.create_agent_bio(bio)

        latest = repo.get_latest_agent_bio(agent_in_db)
        assert latest is not None
        assert latest.persona_bio == "AI-generated persona bio."
        assert latest.persona_bio_source == PersonaBioSource.AI_GENERATED

    def test_get_latest_when_multiple_exist(self, temp_db, agent_in_db):
        """Test that get_latest returns the most recent by created_at."""
        repo = create_sqlite_agent_bio_repository(
            transaction_provider=SqliteTransactionProvider()
        )
        repo.create_agent_bio(
            AgentBio(
                id="bio1",
                agent_id=agent_in_db,
                persona_bio="First bio",
                persona_bio_source=PersonaBioSource.USER_PROVIDED,
                created_at="2026_02_19-09:00:00",
                updated_at="2026_02_19-09:00:00",
            )
        )
        repo.create_agent_bio(
            AgentBio(
                id="bio2",
                agent_id=agent_in_db,
                persona_bio="Second bio",
                persona_bio_source=PersonaBioSource.AI_GENERATED,
                created_at="2026_02_19-10:00:00",
                updated_at="2026_02_19-10:00:00",
            )
        )

        latest = repo.get_latest_agent_bio(agent_in_db)
        assert latest is not None
        assert latest.persona_bio == "Second bio"
        assert latest.id == "bio2"

    def test_list_agent_bios_ordered_by_created_at_desc(self, temp_db, agent_in_db):
        """Test list_agent_bios returns bios in created_at DESC order."""
        repo = create_sqlite_agent_bio_repository(
            transaction_provider=SqliteTransactionProvider()
        )
        repo.create_agent_bio(
            AgentBio(
                id="first",
                agent_id=agent_in_db,
                persona_bio="First",
                persona_bio_source=PersonaBioSource.USER_PROVIDED,
                created_at="2026_02_19-09:00:00",
                updated_at="2026_02_19-09:00:00",
            )
        )
        repo.create_agent_bio(
            AgentBio(
                id="second",
                agent_id=agent_in_db,
                persona_bio="Second",
                persona_bio_source=PersonaBioSource.AI_GENERATED,
                created_at="2026_02_19-10:00:00",
                updated_at="2026_02_19-10:00:00",
            )
        )

        bios = repo.list_agent_bios(agent_in_db)
        assert len(bios) == 2
        assert bios[0].persona_bio == "Second"
        assert bios[1].persona_bio == "First"
