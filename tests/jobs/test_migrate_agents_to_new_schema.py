"""Integration tests for jobs.migrate_agents_to_new_schema."""

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
from db.repositories.generated_bio_repository import (
    create_sqlite_generated_bio_repository,
)
from db.repositories.profile_repository import create_sqlite_profile_repository
from db.repositories.user_agent_profile_metadata_repository import (
    create_sqlite_user_agent_profile_metadata_repository,
)
from jobs.migrate_agents_to_new_schema import main
from lib.timestamp_utils import get_current_timestamp
from simulation.core.models.generated.base import GenerationMetadata
from simulation.core.models.generated.bio import GeneratedBio
from simulation.core.models.profiles import BlueskyProfile


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


def _seed_legacy_data(temp_db: str) -> None:
    """Populate bluesky_profiles and agent_bios (legacy) for migration."""
    import db.adapters.sqlite.sqlite as sqlite_module

    sqlite_module.DB_PATH = temp_db
    initialize_database()

    tx_provider = SqliteTransactionProvider()
    profile_repo = create_sqlite_profile_repository(transaction_provider=tx_provider)
    generated_bio_repo = create_sqlite_generated_bio_repository(
        transaction_provider=tx_provider
    )

    profile1 = BlueskyProfile(
        handle="alice.bsky.social",
        did="did:plc:alice123",
        display_name="Alice",
        bio="Short bio",
        followers_count=100,
        follows_count=50,
        posts_count=10,
    )
    profile_repo.create_or_update_profile(profile1)

    profile2 = BlueskyProfile(
        handle="bob.bsky.social",
        did="did:plc:bob456",
        display_name="Bob",
        bio="",
        followers_count=200,
        follows_count=100,
        posts_count=25,
    )
    profile_repo.create_or_update_profile(profile2)

    generated_bio_repo.create_or_update_generated_bio(
        GeneratedBio(
            handle="alice.bsky.social",
            generated_bio="AI-generated comprehensive bio for Alice.",
            metadata=GenerationMetadata(
                model_used=None,
                generation_metadata=None,
                created_at=get_current_timestamp(),
            ),
        )
    )
    # No generated bio for Bob - migration should use profile.bio or default


class TestMigrateAgentsToNewSchema:
    """Integration tests for the migration job."""

    def test_migration_creates_agents_and_metadata(self, temp_db, capsys):
        """Test that migration creates agent, agent_persona_bios, user_agent_profile_metadata."""
        import db.adapters.sqlite.sqlite as sqlite_module

        _seed_legacy_data(temp_db)
        sqlite_module.DB_PATH = temp_db

        main()

        captured = capsys.readouterr()
        assert "Migrated 2 agents." in captured.out

        agent_repo = create_sqlite_agent_repository(
            transaction_provider=SqliteTransactionProvider()
        )
        agent_bio_repo = create_sqlite_agent_bio_repository(
            transaction_provider=SqliteTransactionProvider()
        )
        metadata_repo = create_sqlite_user_agent_profile_metadata_repository(
            transaction_provider=SqliteTransactionProvider()
        )

        agents = agent_repo.list_all_agents()
        assert len(agents) == 2
        handles = {a.handle for a in agents}
        assert "alice.bsky.social" in handles
        assert "bob.bsky.social" in handles

        alice_agent = agent_repo.get_agent_by_handle("alice.bsky.social")
        assert alice_agent is not None
        assert alice_agent.agent_id == "did:plc:alice123"
        assert alice_agent.display_name == "Alice"

        alice_bio = agent_bio_repo.get_latest_agent_bio("did:plc:alice123")
        assert alice_bio is not None
        assert "AI-generated comprehensive bio" in alice_bio.persona_bio

        bob_bio = agent_bio_repo.get_latest_agent_bio("did:plc:bob456")
        assert bob_bio is not None
        assert bob_bio.persona_bio == "No bio provided."

        alice_meta = metadata_repo.get_by_agent_id("did:plc:alice123")
        assert alice_meta is not None
        assert alice_meta.followers_count == 100
        assert alice_meta.posts_count == 10

        bob_meta = metadata_repo.get_by_agent_id("did:plc:bob456")
        assert bob_meta is not None
        assert bob_meta.followers_count == 200
