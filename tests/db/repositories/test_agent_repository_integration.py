"""Integration tests for db.repositories.agent_repository module."""

import os
import tempfile

import pytest

from db.adapters.sqlite.sqlite import DB_PATH, initialize_database
from db.repositories.agent_repository import create_sqlite_agent_repository
from simulation.core.models.agent import Agent, PersonaSource


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


class TestSQLiteAgentRepositoryIntegration:
    """Integration tests for AgentRepository using a real database."""

    def test_create_and_read_agent(self, temp_db):
        """Test creating an agent and reading it back."""
        repo = create_sqlite_agent_repository()
        agent = Agent(
            agent_id="did:plc:test123",
            handle="test.bsky.social",
            persona_source=PersonaSource.SYNC_BLUESKY,
            display_name="Test User",
            created_at="2026_02_19-10:00:00",
            updated_at="2026_02_19-10:00:00",
        )
        created = repo.create_or_update_agent(agent)
        assert created.agent_id == "did:plc:test123"
        assert created.handle == "test.bsky.social"

        retrieved = repo.get_agent("did:plc:test123")
        assert retrieved is not None
        assert retrieved.agent_id == created.agent_id
        assert retrieved.handle == created.handle
        assert retrieved.persona_source == PersonaSource.SYNC_BLUESKY
        assert retrieved.display_name == created.display_name

    def test_get_agent_by_handle(self, temp_db):
        """Test getting an agent by handle."""
        repo = create_sqlite_agent_repository()
        agent = Agent(
            agent_id="did:plc:abc",
            handle="alice.bsky.social",
            persona_source=PersonaSource.USER_GENERATED,
            display_name="Alice",
            created_at="2026_02_19-10:00:00",
            updated_at="2026_02_19-10:00:00",
        )
        repo.create_or_update_agent(agent)

        retrieved = repo.get_agent_by_handle("alice.bsky.social")
        assert retrieved is not None
        assert retrieved.handle == "alice.bsky.social"
        assert retrieved.agent_id == "did:plc:abc"

    def test_list_all_agents_ordered_by_handle(self, temp_db):
        """Test list_all returns agents ordered by handle."""
        repo = create_sqlite_agent_repository()
        for handle, agent_id in [
            ("zoe.bsky.social", "did:plc:z"),
            ("alice.bsky.social", "did:plc:a"),
        ]:
            repo.create_or_update_agent(
                Agent(
                    agent_id=agent_id,
                    handle=handle,
                    persona_source=PersonaSource.SYNC_BLUESKY,
                    display_name=handle.split(".")[0],
                    created_at="2026_02_19-10:00:00",
                    updated_at="2026_02_19-10:00:00",
                )
            )

        agents = repo.list_all_agents()
        assert len(agents) == 2
        assert agents[0].handle == "alice.bsky.social"
        assert agents[1].handle == "zoe.bsky.social"

    def test_create_or_update_overwrites(self, temp_db):
        """Test that create_or_update_agent overwrites existing agent."""
        repo = create_sqlite_agent_repository()
        agent = Agent(
            agent_id="did:plc:same",
            handle="same.bsky.social",
            persona_source=PersonaSource.SYNC_BLUESKY,
            display_name="Original",
            created_at="2026_02_19-10:00:00",
            updated_at="2026_02_19-10:00:00",
        )
        repo.create_or_update_agent(agent)

        updated = Agent(
            agent_id="did:plc:same",
            handle="same.bsky.social",
            persona_source=PersonaSource.SYNC_BLUESKY,
            display_name="Updated Name",
            created_at="2026_02_19-11:00:00",
            updated_at="2026_02_19-11:00:00",
        )
        repo.create_or_update_agent(updated)

        retrieved = repo.get_agent("did:plc:same")
        assert retrieved is not None
        assert retrieved.display_name == "Updated Name"
        assert retrieved.updated_at == "2026_02_19-11:00:00"
