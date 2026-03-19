"""Integration tests for db.repositories.run_post_like_repository module."""

import sqlite3

import pytest

from db.repositories.run_post_like_repository import (
    create_sqlite_run_post_like_repository,
)
from simulation.core.models.run_post_likes import RunPostLikeSnapshot
from tests.factories import (
    AgentRecordFactory,
    RunAgentSnapshotFactory,
    RunConfigFactory,
    RunPostSnapshotFactory,
)


def _seed_agents(agent_repo, *, agent_ids_handles: list[tuple[str, str]]) -> None:
    for agent_id, handle in agent_ids_handles:
        agent_repo.create_or_update_agent(
            AgentRecordFactory.create(
                agent_id=agent_id,
                handle=handle,
                display_name=handle,
                created_at="2026-03-17T00:00:00Z",
                updated_at="2026-03-17T00:00:00Z",
            )
        )


def _seed_run_membership(
    *,
    run_agent_repo,
    run_id: str,
    agent_ids: list[str],
    handles: list[str],
) -> None:
    snapshots = [
        RunAgentSnapshotFactory.create(
            run_id=run_id,
            agent_id=agent_id,
            selection_order=selection_order,
            handle_at_start=handles[selection_order],
            display_name_at_start=handles[selection_order],
        )
        for selection_order, agent_id in enumerate(agent_ids)
    ]
    run_agent_repo.write_run_agents(run_id, snapshots)


class TestSQLiteRunPostLikeRepositoryIntegration:
    def test_write_and_count_round_trips_includes_zeros(
        self,
        run_repo,
        run_agent_repo,
        run_post_repo,
        agent_repo,
        sqlite_tx,
    ) -> None:
        like_repo = create_sqlite_run_post_like_repository(
            transaction_provider=sqlite_tx
        )

        run = run_repo.create_run(
            RunConfigFactory.create(
                num_agents=2,
                num_turns=1,
                feed_algorithm="chronological",
            )
        )

        _seed_agents(
            agent_repo,
            agent_ids_handles=[
                ("did:plc:agent1", "agent1.bsky.social"),
                ("did:plc:agent2", "agent2.bsky.social"),
            ],
        )

        _seed_run_membership(
            run_agent_repo=run_agent_repo,
            run_id=run.run_id,
            agent_ids=["did:plc:agent1", "did:plc:agent2"],
            handles=["agent1.bsky.social", "agent2.bsky.social"],
        )

        run_posts = [
            RunPostSnapshotFactory.create(
                run_post_id="rp1",
                run_id=run.run_id,
                agent_post_id="ap1",
                author_agent_id="did:plc:agent1",
                author_handle_at_start="agent1.bsky.social",
                author_display_name_at_start="Agent One",
                published_at_start="2026-03-17T10:00:00Z",
                body_text_at_start="Post 1",
                created_at=run.created_at,
            ),
            RunPostSnapshotFactory.create(
                run_post_id="rp2",
                run_id=run.run_id,
                agent_post_id="ap2",
                author_agent_id="did:plc:agent2",
                author_handle_at_start="agent2.bsky.social",
                author_display_name_at_start="Agent Two",
                published_at_start="2026-03-17T11:00:00Z",
                body_text_at_start="Post 2",
                created_at=run.created_at,
            ),
        ]
        run_post_repo.write_run_posts(run.run_id, run_posts)

        like_rows = [
            RunPostLikeSnapshot(
                run_post_like_id="rpl_1",
                run_id=run.run_id,
                run_post_id="rp1",
                liker_agent_id="did:plc:agent1",
                liker_handle_at_start="agent1.bsky.social",
                liker_display_name_at_start="Agent One",
                created_at=run.created_at,
            ),
            RunPostLikeSnapshot(
                run_post_like_id="rpl_2",
                run_id=run.run_id,
                run_post_id="rp1",
                liker_agent_id="did:plc:agent2",
                liker_handle_at_start="agent2.bsky.social",
                liker_display_name_at_start="Agent Two",
                created_at=run.created_at,
            ),
            RunPostLikeSnapshot(
                run_post_like_id="rpl_3",
                run_id=run.run_id,
                run_post_id="rp2",
                liker_agent_id="did:plc:agent1",
                liker_handle_at_start="agent1.bsky.social",
                liker_display_name_at_start="Agent One",
                created_at=run.created_at,
            ),
        ]
        like_repo.write_run_post_likes(run.run_id, like_rows)

        counts = like_repo.count_likes_by_run_post_ids(
            run.run_id, ["rp1", "rp2", "rp_missing"]
        )
        assert counts == {"rp1": 2, "rp2": 1, "rp_missing": 0}

    def test_duplicate_seed_like_raises_integrity_error(
        self,
        run_repo,
        run_agent_repo,
        run_post_repo,
        agent_repo,
        sqlite_tx,
    ) -> None:
        like_repo = create_sqlite_run_post_like_repository(
            transaction_provider=sqlite_tx
        )

        run = run_repo.create_run(
            RunConfigFactory.create(
                num_agents=2,
                num_turns=1,
                feed_algorithm="chronological",
            )
        )

        _seed_agents(
            agent_repo,
            agent_ids_handles=[
                ("did:plc:agent1", "agent1.bsky.social"),
                ("did:plc:agent2", "agent2.bsky.social"),
            ],
        )
        _seed_run_membership(
            run_agent_repo=run_agent_repo,
            run_id=run.run_id,
            agent_ids=["did:plc:agent1", "did:plc:agent2"],
            handles=["agent1.bsky.social", "agent2.bsky.social"],
        )

        run_post_repo.write_run_posts(
            run.run_id,
            [
                RunPostSnapshotFactory.create(
                    run_post_id="rp1",
                    run_id=run.run_id,
                    agent_post_id="ap1",
                    author_agent_id="did:plc:agent1",
                    author_handle_at_start="agent1.bsky.social",
                    author_display_name_at_start="Agent One",
                    published_at_start="2026-03-17T10:00:00Z",
                    body_text_at_start="Post 1",
                    created_at=run.created_at,
                )
            ],
        )

        first = RunPostLikeSnapshot(
            run_post_like_id="rpl_1",
            run_id=run.run_id,
            run_post_id="rp1",
            liker_agent_id="did:plc:agent1",
            liker_handle_at_start="agent1.bsky.social",
            liker_display_name_at_start="Agent One",
            created_at=run.created_at,
        )
        like_repo.write_run_post_likes(run.run_id, [first])

        duplicate = RunPostLikeSnapshot(
            run_post_like_id="rpl_1_dup",
            run_id=run.run_id,
            run_post_id="rp1",
            liker_agent_id="did:plc:agent1",
            liker_handle_at_start="agent1.bsky.social",
            liker_display_name_at_start="Agent One",
            created_at=run.created_at,
        )

        with pytest.raises(sqlite3.IntegrityError):
            like_repo.write_run_post_likes(run.run_id, [duplicate])

    def test_db_constraint_failure_rolls_back_batch(
        self,
        run_repo,
        run_agent_repo,
        run_post_repo,
        agent_repo,
        sqlite_tx,
    ) -> None:
        like_repo = create_sqlite_run_post_like_repository(
            transaction_provider=sqlite_tx
        )

        run = run_repo.create_run(
            RunConfigFactory.create(
                num_agents=2,
                num_turns=1,
                feed_algorithm="chronological",
            )
        )

        _seed_agents(
            agent_repo,
            agent_ids_handles=[
                ("did:plc:agent1", "agent1.bsky.social"),
                ("did:plc:agent2", "agent2.bsky.social"),
            ],
        )
        _seed_run_membership(
            run_agent_repo=run_agent_repo,
            run_id=run.run_id,
            agent_ids=["did:plc:agent1", "did:plc:agent2"],
            handles=["agent1.bsky.social", "agent2.bsky.social"],
        )

        run_post_repo.write_run_posts(
            run.run_id,
            [
                RunPostSnapshotFactory.create(
                    run_post_id="rp1",
                    run_id=run.run_id,
                    agent_post_id="ap1",
                    author_agent_id="did:plc:agent1",
                    author_handle_at_start="agent1.bsky.social",
                    author_display_name_at_start="Agent One",
                    published_at_start="2026-03-17T10:00:00Z",
                    body_text_at_start="Post 1",
                    created_at=run.created_at,
                ),
                RunPostSnapshotFactory.create(
                    run_post_id="rp2",
                    run_id=run.run_id,
                    agent_post_id="ap2",
                    author_agent_id="did:plc:agent2",
                    author_handle_at_start="agent2.bsky.social",
                    author_display_name_at_start="Agent Two",
                    published_at_start="2026-03-17T11:00:00Z",
                    body_text_at_start="Post 2",
                    created_at=run.created_at,
                ),
            ],
        )

        valid_row = RunPostLikeSnapshot(
            run_post_like_id="rpl_valid",
            run_id=run.run_id,
            run_post_id="rp1",
            liker_agent_id="did:plc:agent1",
            liker_handle_at_start="agent1.bsky.social",
            liker_display_name_at_start="Agent One",
            created_at=run.created_at,
        )
        invalid_row = RunPostLikeSnapshot(
            run_post_like_id="rpl_invalid",
            run_id=run.run_id,
            run_post_id="rp1",
            liker_agent_id="did:plc:missing",
            liker_handle_at_start="missing.bsky.social",
            liker_display_name_at_start="Missing",
            created_at=run.created_at,
        )

        with pytest.raises(sqlite3.IntegrityError):
            like_repo.write_run_post_likes(run.run_id, [valid_row, invalid_row])

        counts = like_repo.count_likes_by_run_post_ids(run.run_id, ["rp1", "rp2"])
        assert counts == {"rp1": 0, "rp2": 0}
