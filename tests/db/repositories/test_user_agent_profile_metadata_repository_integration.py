"""Integration tests for db.repositories.user_agent_profile_metadata_repository module."""

from simulation.core.models.user_agent_profile_metadata import UserAgentProfileMetadata


class TestSQLiteUserAgentProfileMetadataRepositoryIntegration:
    """Integration tests for UserAgentProfileMetadataRepository using a real database."""

    def test_create_and_get_by_agent_id(
        self, user_agent_profile_metadata_repo, agent_in_db_meta
    ):
        """Test creating metadata and retrieving by agent_id."""
        repo = user_agent_profile_metadata_repo
        agent_id = agent_in_db_meta
        metadata = UserAgentProfileMetadata(
            id="meta1",
            agent_id=agent_id,
            followers_count=1000,
            follows_count=200,
            posts_count=50,
            created_at="2026_02_19-10:00:00",
            updated_at="2026_02_19-10:00:00",
        )
        repo.create_or_update_metadata(metadata)

        retrieved = repo.get_by_agent_id(agent_id)
        assert retrieved is not None
        assert retrieved.followers_count == 1000
        assert retrieved.follows_count == 200
        assert retrieved.posts_count == 50

    def test_create_or_update_overwrites(
        self, user_agent_profile_metadata_repo, agent_in_db_meta
    ):
        """Test that create_or_update_metadata overwrites existing metadata."""
        repo = user_agent_profile_metadata_repo
        agent_id = agent_in_db_meta
        repo.create_or_update_metadata(
            UserAgentProfileMetadata(
                id="meta1",
                agent_id=agent_id,
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
                agent_id=agent_id,
                followers_count=5000,
                follows_count=300,
                posts_count=200,
                created_at="2026_02_19-10:00:00",
                updated_at="2026_02_19-10:00:00",
            )
        )

        retrieved = repo.get_by_agent_id(agent_id)
        assert retrieved is not None
        assert retrieved.followers_count == 5000
        assert retrieved.follows_count == 300
        assert retrieved.posts_count == 200
