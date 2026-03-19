"""Integration tests for db.repositories.run_post_comment_repository module."""

import sqlite3

import pytest

from db.repositories.run_post_comment_repository import (
    create_sqlite_run_post_comment_repository,
)
from simulation.core.models.run_post_comments import RunPostCommentSnapshot
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


class TestSQLiteRunPostCommentRepositoryIntegration:
    def test_write_and_count_round_trips_includes_zeros(
        self,
        run_repo,
        run_agent_repo,
        run_post_repo,
        agent_repo,
        sqlite_tx,
    ) -> None:
        comment_repo = create_sqlite_run_post_comment_repository(
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

        comment_rows = [
            RunPostCommentSnapshot(
                run_post_comment_id="rpc_1",
                run_id=run.run_id,
                run_post_id="rp1",
                author_agent_id="did:plc:agent1",
                author_handle_at_start="agent1.bsky.social",
                author_display_name_at_start="Agent One",
                body_text_at_start="c1",
                published_at_start="2026-03-17T10:01:00Z",
                created_at=run.created_at,
            ),
            RunPostCommentSnapshot(
                run_post_comment_id="rpc_2",
                run_id=run.run_id,
                run_post_id="rp1",
                author_agent_id="did:plc:agent2",
                author_handle_at_start="agent2.bsky.social",
                author_display_name_at_start="Agent Two",
                body_text_at_start="c2",
                published_at_start="2026-03-17T10:02:00Z",
                created_at=run.created_at,
            ),
            RunPostCommentSnapshot(
                run_post_comment_id="rpc_3",
                run_id=run.run_id,
                run_post_id="rp2",
                author_agent_id="did:plc:agent1",
                author_handle_at_start="agent1.bsky.social",
                author_display_name_at_start="Agent One",
                body_text_at_start="c3",
                published_at_start="2026-03-17T11:01:00Z",
                created_at=run.created_at,
            ),
        ]
        comment_repo.write_run_post_comments(run.run_id, comment_rows)

        counts = comment_repo.count_comments_by_run_post_ids(
            run.run_id, ["rp1", "rp2", "rp_missing"]
        )
        assert counts == {"rp1": 2, "rp2": 1, "rp_missing": 0}

    def test_db_constraint_failure_rolls_back_batch(
        self,
        run_repo,
        run_agent_repo,
        run_post_repo,
        agent_repo,
        sqlite_tx,
    ) -> None:
        comment_repo = create_sqlite_run_post_comment_repository(
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

        valid_row = RunPostCommentSnapshot(
            run_post_comment_id="rpc_valid",
            run_id=run.run_id,
            run_post_id="rp1",
            author_agent_id="did:plc:agent1",
            author_handle_at_start="agent1.bsky.social",
            author_display_name_at_start="Agent One",
            body_text_at_start="ok",
            published_at_start="2026-03-17T10:01:00Z",
            created_at=run.created_at,
        )
        invalid_row = RunPostCommentSnapshot(
            run_post_comment_id="rpc_invalid",
            run_id=run.run_id,
            run_post_id="rp1",
            author_agent_id="did:plc:missing",
            author_handle_at_start="missing.bsky.social",
            author_display_name_at_start="Missing",
            body_text_at_start="bad",
            published_at_start="2026-03-17T10:02:00Z",
            created_at=run.created_at,
        )

        with pytest.raises(sqlite3.IntegrityError):
            comment_repo.write_run_post_comments(run.run_id, [valid_row, invalid_row])

        counts = comment_repo.count_comments_by_run_post_ids(run.run_id, ["rp1", "rp2"])
        assert counts == {"rp1": 0, "rp2": 0}
