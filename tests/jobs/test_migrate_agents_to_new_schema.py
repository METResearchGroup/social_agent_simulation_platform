"""Integration tests for jobs.migrate_agents_to_new_schema."""

from jobs.migrate_agents_to_new_schema import main
from lib.timestamp_utils import get_current_timestamp
from tests.factories import (
    BlueskyProfileFactory,
    GeneratedBioFactory,
    GenerationMetadataFactory,
)


def _seed_legacy_data(profile_repo, generated_bio_repo) -> None:
    """Populate bluesky_profiles and agent_bios (legacy) for migration."""
    profile1 = BlueskyProfileFactory.create(
        handle="alice.bsky.social",
        did="did:plc:alice123",
        display_name="Alice",
        bio="Short bio",
        followers_count=100,
        follows_count=50,
        posts_count=10,
    )
    profile_repo.create_or_update_profile(profile1)

    profile2 = BlueskyProfileFactory.create(
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
        GeneratedBioFactory.create(
            handle="alice.bsky.social",
            generated_bio="AI-generated comprehensive bio for Alice.",
            metadata=GenerationMetadataFactory.create(
                model_used=None,
                generation_metadata=None,
                created_at=get_current_timestamp(),
            ),
        )
    )
    # No generated bio for Bob - migration should use profile.bio or default


class TestMigrateAgentsToNewSchema:
    """Integration tests for the migration job."""

    def test_migration_creates_agents_and_metadata(
        self,
        profile_repo,
        generated_bio_repo,
        agent_repo,
        agent_bio_repo,
        user_agent_profile_metadata_repo,
        capsys,
    ):
        """Test that migration creates agent, agent_persona_bios, user_agent_profile_metadata."""
        _seed_legacy_data(profile_repo, generated_bio_repo)

        main()

        captured = capsys.readouterr()
        assert "Migrated 2 agents." in captured.out

        metadata_repo = user_agent_profile_metadata_repo

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
