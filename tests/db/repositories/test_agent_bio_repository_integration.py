"""Integration tests for db.repositories.agent_bio_repository module."""

from simulation.core.models.agent_bio import AgentBio, PersonaBioSource


class TestSQLiteAgentBioRepositoryIntegration:
    """Integration tests for AgentBioRepository using a real database."""

    def test_create_and_get_latest_bio(self, agent_bio_repo, agent_in_db):
        """Test creating a bio and retrieving it as latest."""
        repo = agent_bio_repo
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

    def test_get_latest_when_multiple_exist(self, agent_bio_repo, agent_in_db):
        """Test that get_latest returns the most recent by created_at."""
        repo = agent_bio_repo
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

    def test_list_agent_bios_ordered_by_created_at_desc(
        self, agent_bio_repo, agent_in_db
    ):
        """Test list_agent_bios returns bios in created_at DESC order."""
        repo = agent_bio_repo
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
