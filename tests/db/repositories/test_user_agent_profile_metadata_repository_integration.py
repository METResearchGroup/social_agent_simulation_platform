"""Integration tests for db.repositories.user_agent_profile_metadata_repository module."""

import os
import tempfile

import pytest

from db.adapters.sqlite.sqlite import DB_PATH, initialize_database
from db.repositories.agent_repository import create_sqlite_agent_repository
from db.repositories.user_agent_profile_metadata_repository import (
    create_sqlite_user_agent_profile_metadata_repository,
)
from simulation.core.models.agent import Agent, PersonaSource
from simulation.core.models.user_agent_profile_metadata import UserAgentProfileMetadata


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
    """Create an agent in the database for metadata tests."""
    agent_repo = create_sqlite_agent_repository()
    agent = Agent(
        agent_id="did:plc:meta123",
        handle="meta.bsky.social",
        persona_source=PersonaSource.SYNC_BLUESKY,
        display_name="Meta User",
        created_at="2026_02_19-10:00:00",
        updated_at="2026_02_19-10:00:00",
    )
    agent_repo.create_or_update_agent(agent)
    return "did:plc:meta123"


class TestSQLiteUserAgentProfileMetadataRepositoryIntegration:
    """Integration tests for UserAgentProfileMetadataRepository using a real database."""

    def test_create_and_get_by_agent_id(self, temp_db, agent_in_db):
        """Test creating metadata and retrieving by agent_id."""
        repo = create_sqlite_user_agent_profile_metadata_repository()
        metadata = UserAgentProfileMetadata(
            id="meta1",
            agent_id=agent_in_db,
            followers_count=1000,
            follows_count=200,
            posts_count=50,
            created_at="2026_02_19-10:00:00",
            updated_at="2026_02_19-10:00:00",
        )
        repo.create_or_update_metadata(metadata)

        retrieved = repo.get_by_agent_id(agent_in_db)
        assert retrieved is not None
        assert retrieved.followers_count == 1000
        assert retrieved.follows_count == 200
        assert retrieved.posts_count == 50

    def test_create_or_update_overwrites(self, temp_db, agent_in_db):
        """Test that create_or_update_metadata overwrites existing metadata."""
        repo = create_sqlite_user_agent_profile_metadata_repository()
        repo.create_or_update_metadata(
            UserAgentProfileMetadata(
                id="meta1",
                agent_id=agent_in_db,
                followers_count=100,
                follows_count=50,
                posts_count=10,
                created_at="2026_02_19-09:00:00",
                updated_at="2026_02_19-09:00:00",
            )
        )

        repo.create_or_update_metadata(
            UserAgentProfileMetadata(
                id="meta2",
                agent_id=agent_in_db,
                followers_count=5000,
                follows_count=300,
                posts_count=200,
                created_at="2026_02_19-10:00:00",
                updated_at="2026_02_19-10:00:00",
            )
        )

        retrieved = repo.get_by_agent_id(agent_in_db)
        assert retrieved is not None
        assert retrieved.followers_count == 5000
        assert retrieved.follows_count == 300
        assert retrieved.posts_count == 200
