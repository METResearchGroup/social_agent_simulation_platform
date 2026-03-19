"""Integration tests for db.repositories.run_post_repository module."""

import sqlite3

import pytest

from tests.factories import (
    AgentRecordFactory,
    RunAgentSnapshotFactory,
    RunConfigFactory,
    RunPostSnapshotFactory,
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


class TestSQLiteRunPostRepositoryIntegration:
    def test_write_and_list_run_posts_round_trips(
        self,
        run_repo,
        run_agent_repo,
        run_post_repo,
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
            RunPostSnapshotFactory.create(
                run_post_id="rp_post1",
                run_id=run.run_id,
                agent_post_id="ap_post1",
                author_agent_id="did:plc:agent1",
                author_handle_at_start="agent1.bsky.social",
                author_display_name_at_start="Agent One",
                body_text_at_start="First post body",
                published_at_start="2026-03-17T10:00:00Z",
                created_at=run.created_at,
            ),
            RunPostSnapshotFactory.create(
                run_post_id="rp_post2",
                run_id=run.run_id,
                agent_post_id="ap_post2",
                author_agent_id="did:plc:agent2",
                author_handle_at_start="agent2.bsky.social",
                author_display_name_at_start="Agent Two",
                body_text_at_start="Second post body",
                published_at_start="2026-03-17T11:00:00Z",
                created_at=run.created_at,
            ),
        ]

        run_post_repo.write_run_posts(run.run_id, snapshots)

        result = run_post_repo.list_run_posts(run.run_id)

        assert len(result) == 2
        assert [snapshot.run_post_id for snapshot in result] == ["rp_post1", "rp_post2"]
        assert result[0].body_text_at_start == "First post body"
        assert result[1].body_text_at_start == "Second post body"
        assert result[0].author_handle_at_start == "agent1.bsky.social"
        assert result[1].author_handle_at_start == "agent2.bsky.social"

    def test_read_run_posts_by_ids_returns_ordered_preserves_input_skips_missing(
        self,
        run_repo,
        run_agent_repo,
        run_post_repo,
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
            RunPostSnapshotFactory.create(
                run_post_id="rp_a",
                run_id=run.run_id,
                agent_post_id="ap_a",
                author_agent_id="did:plc:agent1",
                author_handle_at_start="agent1.bsky.social",
                body_text_at_start="Post A",
                published_at_start="2026-03-17T10:00:00Z",
                created_at=run.created_at,
            ),
            RunPostSnapshotFactory.create(
                run_post_id="rp_b",
                run_id=run.run_id,
                agent_post_id="ap_b",
                author_agent_id="did:plc:agent2",
                author_handle_at_start="agent2.bsky.social",
                body_text_at_start="Post B",
                published_at_start="2026-03-17T11:00:00Z",
                created_at=run.created_at,
            ),
        ]
        run_post_repo.write_run_posts(run.run_id, snapshots)

        result = run_post_repo.read_run_posts_by_ids(
            run.run_id, ["rp_b", "rp_nonexistent", "rp_a"]
        )

        assert len(result) == 2
        assert result[0].run_post_id == "rp_b"
        assert result[0].body_text_at_start == "Post B"
        assert result[1].run_post_id == "rp_a"
        assert result[1].body_text_at_start == "Post A"

    def test_deterministic_ordering(
        self,
        run_repo,
        run_agent_repo,
        run_post_repo,
        agent_repo,
    ):
        run = run_repo.create_run(
            RunConfigFactory.create(
                num_agents=2,
                num_turns=1,
                feed_algorithm="chronological",
            )
        )
        _seed_agent(agent_repo, agent_id="did:plc:agent1", handle="agent1.bsky.social")
        _seed_agent(agent_repo, agent_id="did:plc:agent2", handle="agent2.bsky.social")
        _seed_run_membership(
            run_agent_repo=run_agent_repo,
            run_id=run.run_id,
            agent_ids=["did:plc:agent1", "did:plc:agent2"],
        )

        snapshots = [
            RunPostSnapshotFactory.create(
                run_post_id="rp_b",
                run_id=run.run_id,
                agent_post_id="ap_b",
                author_agent_id="did:plc:agent2",
                published_at_start="2026-03-17T11:00:00Z",
                created_at=run.created_at,
            ),
            RunPostSnapshotFactory.create(
                run_post_id="rp_a",
                run_id=run.run_id,
                agent_post_id="ap_a",
                author_agent_id="did:plc:agent1",
                published_at_start="2026-03-17T10:00:00Z",
                created_at=run.created_at,
            ),
        ]
        run_post_repo.write_run_posts(run.run_id, snapshots)

        result = run_post_repo.list_run_posts(run.run_id)

        assert [snapshot.author_agent_id for snapshot in result] == [
            "did:plc:agent1",
            "did:plc:agent2",
        ]

    def test_duplicate_agent_post_id_raises_integrity_error(
        self,
        run_repo,
        run_agent_repo,
        run_post_repo,
        agent_repo,
    ):
        run = run_repo.create_run(
            RunConfigFactory.create(
                num_agents=1,
                num_turns=1,
                feed_algorithm="chronological",
            )
        )
        _seed_agent(agent_repo, agent_id="did:plc:agent1", handle="agent1.bsky.social")
        _seed_run_membership(
            run_agent_repo=run_agent_repo,
            run_id=run.run_id,
            agent_ids=["did:plc:agent1"],
        )

        snapshot = RunPostSnapshotFactory.create(
            run_post_id="rp_1",
            run_id=run.run_id,
            agent_post_id="ap_same",
            author_agent_id="did:plc:agent1",
            created_at=run.created_at,
        )
        run_post_repo.write_run_posts(run.run_id, [snapshot])

        with pytest.raises(sqlite3.IntegrityError):
            run_post_repo.write_run_posts(
                run.run_id,
                [
                    RunPostSnapshotFactory.create(
                        run_post_id="rp_2",
                        run_id=run.run_id,
                        agent_post_id="ap_same",
                        author_agent_id="did:plc:agent1",
                        created_at=run.created_at,
                    ),
                ],
            )

        assert len(run_post_repo.list_run_posts(run.run_id)) == 1

    def test_author_fk_failure_rolls_back_batch(
        self,
        run_repo,
        run_agent_repo,
        run_post_repo,
        agent_repo,
    ):
        run = run_repo.create_run(
            RunConfigFactory.create(
                num_agents=2,
                num_turns=1,
                feed_algorithm="chronological",
            )
        )
        _seed_agent(agent_repo, agent_id="did:plc:agent1", handle="agent1.bsky.social")
        _seed_agent(agent_repo, agent_id="did:plc:agent2", handle="agent2.bsky.social")
        _seed_run_membership(
            run_agent_repo=run_agent_repo,
            run_id=run.run_id,
            agent_ids=["did:plc:agent1", "did:plc:agent2"],
        )

        with pytest.raises(sqlite3.IntegrityError):
            run_post_repo.write_run_posts(
                run.run_id,
                [
                    RunPostSnapshotFactory.create(
                        run_post_id="rp_1",
                        run_id=run.run_id,
                        agent_post_id="ap_1",
                        author_agent_id="did:plc:agent1",
                        created_at=run.created_at,
                    ),
                    RunPostSnapshotFactory.create(
                        run_post_id="rp_2",
                        run_id=run.run_id,
                        agent_post_id="ap_2",
                        author_agent_id="did:plc:nonexistent",
                        created_at=run.created_at,
                    ),
                ],
            )

        assert run_post_repo.list_run_posts(run.run_id) == []
