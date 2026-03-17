"""Integration tests for db.repositories.run_follow_edge_repository module."""

import sqlite3

import pytest

from tests.factories import (
    AgentRecordFactory,
    RunAgentSnapshotFactory,
    RunConfigFactory,
    RunFollowEdgeSnapshotFactory,
)


def _seed_agent(agent_repo, *, agent_id: str, handle: str) -> None:
    agent_repo.create_or_update_agent(
        AgentRecordFactory.create(
            agent_id=agent_id,
            handle=handle,
            display_name=handle,
            created_at="2026-03-17T00:00:00Z",
            updated_at="2026-03-17T00:00:00Z",
        )
    )


def _seed_run_membership(*, run_agent_repo, run_id: str, agent_ids: list[str]) -> None:
    snapshots = [
        RunAgentSnapshotFactory.create(
            run_id=run_id,
            agent_id=agent_id,
            selection_order=selection_order,
            handle_at_start=f"agent{selection_order + 1}.bsky.social",
        )
        for selection_order, agent_id in enumerate(agent_ids)
    ]
    run_agent_repo.write_run_agents(run_id, snapshots)


class TestSQLiteRunFollowEdgeRepositoryIntegration:
    def test_write_and_list_run_follow_edges_round_trips(
        self,
        run_repo,
        run_agent_repo,
        run_follow_edge_repo,
        agent_repo,
    ):
        run = run_repo.create_run(
            RunConfigFactory.create(
                num_agents=2,
                num_turns=1,
                feed_algorithm="chronological",
            )
        )
        _seed_agent(
            agent_repo,
            agent_id="did:plc:agent1",
            handle="agent1.bsky.social",
        )
        _seed_agent(
            agent_repo,
            agent_id="did:plc:agent2",
            handle="agent2.bsky.social",
        )
        _seed_run_membership(
            run_agent_repo=run_agent_repo,
            run_id=run.run_id,
            agent_ids=["did:plc:agent1", "did:plc:agent2"],
        )

        snapshots = [
            RunFollowEdgeSnapshotFactory.create(
                run_id=run.run_id,
                follower_agent_id="did:plc:agent1",
                target_agent_id="did:plc:agent2",
                created_at=run.created_at,
            )
        ]

        run_follow_edge_repo.write_run_follow_edges(run.run_id, snapshots)

        result = run_follow_edge_repo.list_run_follow_edges(run.run_id)

        assert [
            (snapshot.follower_agent_id, snapshot.target_agent_id)
            for snapshot in result
        ] == [("did:plc:agent1", "did:plc:agent2")]
        assert result[0].created_at == run.created_at

    def test_duplicate_snapshot_raises_integrity_error(
        self,
        run_repo,
        run_agent_repo,
        run_follow_edge_repo,
        agent_repo,
    ):
        run = run_repo.create_run(
            RunConfigFactory.create(
                num_agents=2,
                num_turns=1,
                feed_algorithm="chronological",
            )
        )
        _seed_agent(
            agent_repo,
            agent_id="did:plc:agent1",
            handle="agent1.bsky.social",
        )
        _seed_agent(
            agent_repo,
            agent_id="did:plc:agent2",
            handle="agent2.bsky.social",
        )
        _seed_run_membership(
            run_agent_repo=run_agent_repo,
            run_id=run.run_id,
            agent_ids=["did:plc:agent1", "did:plc:agent2"],
        )

        snapshot = RunFollowEdgeSnapshotFactory.create(
            run_id=run.run_id,
            follower_agent_id="did:plc:agent1",
            target_agent_id="did:plc:agent2",
            created_at=run.created_at,
        )
        run_follow_edge_repo.write_run_follow_edges(run.run_id, [snapshot])

        with pytest.raises(sqlite3.IntegrityError):
            run_follow_edge_repo.write_run_follow_edges(run.run_id, [snapshot])

        assert run_follow_edge_repo.list_run_follow_edges(run.run_id) == [snapshot]

    def test_membership_fk_failure_rolls_back_batch(
        self,
        run_repo,
        run_agent_repo,
        run_follow_edge_repo,
        agent_repo,
    ):
        run = run_repo.create_run(
            RunConfigFactory.create(
                num_agents=3,
                num_turns=1,
                feed_algorithm="chronological",
            )
        )
        _seed_agent(
            agent_repo,
            agent_id="did:plc:agent1",
            handle="agent1.bsky.social",
        )
        _seed_agent(
            agent_repo,
            agent_id="did:plc:agent2",
            handle="agent2.bsky.social",
        )
        _seed_agent(
            agent_repo,
            agent_id="did:plc:agent3",
            handle="agent3.bsky.social",
        )
        _seed_run_membership(
            run_agent_repo=run_agent_repo,
            run_id=run.run_id,
            agent_ids=["did:plc:agent1", "did:plc:agent2"],
        )

        with pytest.raises(sqlite3.IntegrityError):
            run_follow_edge_repo.write_run_follow_edges(
                run.run_id,
                [
                    RunFollowEdgeSnapshotFactory.create(
                        run_id=run.run_id,
                        follower_agent_id="did:plc:agent1",
                        target_agent_id="did:plc:agent2",
                        created_at=run.created_at,
                    ),
                    RunFollowEdgeSnapshotFactory.create(
                        run_id=run.run_id,
                        follower_agent_id="did:plc:agent2",
                        target_agent_id="did:plc:agent3",
                        created_at=run.created_at,
                    ),
                ],
            )

        assert run_follow_edge_repo.list_run_follow_edges(run.run_id) == []
