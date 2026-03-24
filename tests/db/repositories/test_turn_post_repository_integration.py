"""Integration tests for turn post read repository."""

from lib.agent_id import canonical_agent_id
from tests.factories import (
    AgentRecordFactory,
    RunAgentSnapshotFactory,
    RunConfigFactory,
    TurnMetadataFactory,
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


class TestSQLiteTurnPostRepositoryIntegration:
    def test_read_turn_posts_by_ids_preserves_order_skips_missing(
        self,
        run_repo,
        run_agent_repo,
        turn_post_repo,
        agent_repo,
    ):
        run = run_repo.create_run(
            RunConfigFactory.create(
                num_agents=1,
                num_turns=1,
                feed_algorithm="chronological",
            )
        )
        agent_id = canonical_agent_id("author.bsky.social")
        _seed_agent(agent_repo, agent_id=agent_id, handle="author.bsky.social")
        run_agent_repo.write_run_agents(
            run.run_id,
            [
                RunAgentSnapshotFactory.create(
                    run_id=run.run_id,
                    agent_id=agent_id,
                    selection_order=0,
                    handle_at_start="author.bsky.social",
                )
            ],
        )
        run_repo.write_turn_metadata(
            TurnMetadataFactory.create(
                run_id=run.run_id,
                turn_number=0,
                total_actions={},
                created_at=run.created_at,
            )
        )

        from db.adapters.sqlite.sqlite import get_connection

        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO turn_posts (
                    turn_post_id, run_id, turn_number, author_agent_id,
                    author_handle_at_time, author_display_name_at_time,
                    body_text, created_at, explanation, model_used,
                    generation_metadata_json, generation_created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "tp_alpha",
                    run.run_id,
                    0,
                    agent_id,
                    "author.bsky.social",
                    "Author",
                    "alpha body",
                    "2026-03-17T10:00:00Z",
                    None,
                    None,
                    None,
                    None,
                ),
            )
            conn.execute(
                """
                INSERT INTO turn_posts (
                    turn_post_id, run_id, turn_number, author_agent_id,
                    author_handle_at_time, author_display_name_at_time,
                    body_text, created_at, explanation, model_used,
                    generation_metadata_json, generation_created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "tp_beta",
                    run.run_id,
                    0,
                    agent_id,
                    "author.bsky.social",
                    "Author",
                    "beta body",
                    "2026-03-17T11:00:00Z",
                    None,
                    None,
                    None,
                    None,
                ),
            )
            conn.commit()

        result = turn_post_repo.read_turn_posts_by_ids(
            run.run_id, ["tp_missing", "tp_beta", "tp_alpha"]
        )

        assert len(result) == 2
        assert result[0].turn_post_id == "tp_beta"
        assert result[0].body_text == "beta body"
        assert result[1].turn_post_id == "tp_alpha"
        assert result[1].body_text == "alpha body"

    def test_get_by_post_ids_empty_input_returns_empty(
        self,
        run_repo,
        run_agent_repo,
        turn_post_repo,
        agent_repo,
    ):
        run = run_repo.create_run(
            RunConfigFactory.create(
                num_agents=1,
                num_turns=1,
                feed_algorithm="chronological",
            )
        )
        agent_id = canonical_agent_id("author2.bsky.social")
        _seed_agent(agent_repo, agent_id=agent_id, handle="author2.bsky.social")
        run_agent_repo.write_run_agents(
            run.run_id,
            [
                RunAgentSnapshotFactory.create(
                    run_id=run.run_id,
                    agent_id=agent_id,
                    selection_order=0,
                    handle_at_start="author2.bsky.social",
                )
            ],
        )
        run_repo.write_turn_metadata(
            TurnMetadataFactory.create(
                run_id=run.run_id,
                turn_number=0,
                total_actions={},
                created_at=run.created_at,
            )
        )

        assert turn_post_repo.read_turn_posts_by_ids(run.run_id, []) == []

    def test_get_by_post_ids_all_missing_returns_empty(
        self,
        run_repo,
        run_agent_repo,
        turn_post_repo,
        agent_repo,
    ):
        run = run_repo.create_run(
            RunConfigFactory.create(
                num_agents=1,
                num_turns=1,
                feed_algorithm="chronological",
            )
        )
        agent_id = canonical_agent_id("author3.bsky.social")
        _seed_agent(agent_repo, agent_id=agent_id, handle="author3.bsky.social")
        run_agent_repo.write_run_agents(
            run.run_id,
            [
                RunAgentSnapshotFactory.create(
                    run_id=run.run_id,
                    agent_id=agent_id,
                    selection_order=0,
                    handle_at_start="author3.bsky.social",
                )
            ],
        )
        run_repo.write_turn_metadata(
            TurnMetadataFactory.create(
                run_id=run.run_id,
                turn_number=0,
                total_actions={},
                created_at=run.created_at,
            )
        )

        assert (
            turn_post_repo.read_turn_posts_by_ids(
                run.run_id, ["tp_no_such_1", "tp_no_such_2"]
            )
            == []
        )
