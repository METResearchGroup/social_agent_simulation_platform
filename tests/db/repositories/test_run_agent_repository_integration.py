"""Integration tests for db.repositories.run_agent_repository module."""

import sqlite3

import pytest

from tests.factories import (
    AgentBioFactory,
    AgentRecordFactory,
    RunAgentSnapshotFactory,
    RunConfigFactory,
    UserAgentProfileMetadataFactory,
)


def _seed_agent_snapshot_dependencies(
    *,
    agent_repo,
    agent_bio_repo,
    user_agent_profile_metadata_repo,
    agent_id: str,
    handle: str,
    display_name: str,
) -> None:
    agent_repo.create_or_update_agent(
        AgentRecordFactory.create(
            agent_id=agent_id,
            handle=handle,
            display_name=display_name,
            created_at="2026-03-13T00:00:00Z",
            updated_at="2026-03-13T00:00:00Z",
        )
    )
    agent_bio_repo.create_agent_bio(
        AgentBioFactory.create(
            agent_id=agent_id,
            persona_bio=f"{display_name} bio",
            created_at="2026-03-13T00:00:00Z",
            updated_at="2026-03-13T00:00:00Z",
        )
    )
    user_agent_profile_metadata_repo.create_or_update_metadata(
        UserAgentProfileMetadataFactory.create(
            agent_id=agent_id,
            followers_count=10,
            follows_count=11,
            posts_count=12,
            created_at="2026-03-13T00:00:00Z",
            updated_at="2026-03-13T00:00:00Z",
        )
    )


class TestSQLiteRunAgentRepositoryIntegration:
    def test_write_and_list_run_agents_round_trips(
        self,
        run_repo,
        run_agent_repo,
        agent_repo,
        agent_bio_repo,
        user_agent_profile_metadata_repo,
    ):
        run = run_repo.create_run(
            RunConfigFactory.create(
                num_agents=2,
                num_turns=1,
                feed_algorithm="chronological",
            )
        )
        _seed_agent_snapshot_dependencies(
            agent_repo=agent_repo,
            agent_bio_repo=agent_bio_repo,
            user_agent_profile_metadata_repo=user_agent_profile_metadata_repo,
            agent_id="did:plc:agent1",
            handle="agent1.bsky.social",
            display_name="Agent One",
        )
        _seed_agent_snapshot_dependencies(
            agent_repo=agent_repo,
            agent_bio_repo=agent_bio_repo,
            user_agent_profile_metadata_repo=user_agent_profile_metadata_repo,
            agent_id="did:plc:agent2",
            handle="agent2.bsky.social",
            display_name="Agent Two",
        )

        snapshots = [
            RunAgentSnapshotFactory.create(
                run_id=run.run_id,
                agent_id="did:plc:agent1",
                selection_order=0,
                handle_at_start="agent1.bsky.social",
                display_name_at_start="Agent One",
                persona_bio_at_start="Agent One bio",
                followers_count_at_start=10,
                follows_count_at_start=11,
                posts_count_at_start=12,
                created_at=run.created_at,
            ),
            RunAgentSnapshotFactory.create(
                run_id=run.run_id,
                agent_id="did:plc:agent2",
                selection_order=1,
                handle_at_start="agent2.bsky.social",
                display_name_at_start="Agent Two",
                persona_bio_at_start="Agent Two bio",
                followers_count_at_start=20,
                follows_count_at_start=21,
                posts_count_at_start=22,
                created_at=run.created_at,
            ),
        ]

        run_agent_repo.write_run_agents(run.run_id, snapshots)

        result = run_agent_repo.list_run_agents(run.run_id)

        assert [snapshot.selection_order for snapshot in result] == [0, 1]
        assert [snapshot.agent_id for snapshot in result] == [
            "did:plc:agent1",
            "did:plc:agent2",
        ]
        assert result[0].display_name_at_start == "Agent One"
        assert result[1].display_name_at_start == "Agent Two"

    def test_duplicate_selection_order_raises_integrity_error(
        self,
        run_repo,
        run_agent_repo,
        agent_repo,
        agent_bio_repo,
        user_agent_profile_metadata_repo,
    ):
        run = run_repo.create_run(
            RunConfigFactory.create(
                num_agents=2,
                num_turns=1,
                feed_algorithm="chronological",
            )
        )
        _seed_agent_snapshot_dependencies(
            agent_repo=agent_repo,
            agent_bio_repo=agent_bio_repo,
            user_agent_profile_metadata_repo=user_agent_profile_metadata_repo,
            agent_id="did:plc:agent1",
            handle="agent1.bsky.social",
            display_name="Agent One",
        )
        _seed_agent_snapshot_dependencies(
            agent_repo=agent_repo,
            agent_bio_repo=agent_bio_repo,
            user_agent_profile_metadata_repo=user_agent_profile_metadata_repo,
            agent_id="did:plc:agent2",
            handle="agent2.bsky.social",
            display_name="Agent Two",
        )

        with pytest.raises(sqlite3.IntegrityError):
            run_agent_repo.write_run_agents(
                run.run_id,
                [
                    RunAgentSnapshotFactory.create(
                        run_id=run.run_id,
                        agent_id="did:plc:agent1",
                        selection_order=0,
                        handle_at_start="agent1.bsky.social",
                    ),
                    RunAgentSnapshotFactory.create(
                        run_id=run.run_id,
                        agent_id="did:plc:agent2",
                        selection_order=0,
                        handle_at_start="agent2.bsky.social",
                    ),
                ],
            )
