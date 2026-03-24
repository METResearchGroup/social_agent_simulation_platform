"""Integration tests for turn post repository."""

from lib.agent_id import canonical_agent_id
from lib.timestamp_utils import get_current_timestamp
from simulation.core.models.turn_posts import TurnPostSnapshot
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

    def test_write_and_list_before_turn_and_at_turn(
        self,
        run_repo,
        run_agent_repo,
        turn_post_repo,
        agent_repo,
    ):
        run = run_repo.create_run(
            RunConfigFactory.create(
                num_agents=1,
                num_turns=2,
                feed_algorithm="chronological",
            )
        )
        agent_id = canonical_agent_id("writer.bsky.social")
        _seed_agent(agent_repo, agent_id=agent_id, handle="writer.bsky.social")
        run_agent_repo.write_run_agents(
            run.run_id,
            [
                RunAgentSnapshotFactory.create(
                    run_id=run.run_id,
                    agent_id=agent_id,
                    selection_order=0,
                    handle_at_start="writer.bsky.social",
                )
            ],
        )
        for turn_number in (0, 1):
            run_repo.write_turn_metadata(
                TurnMetadataFactory.create(
                    run_id=run.run_id,
                    turn_number=turn_number,
                    total_actions={},
                    created_at=run.created_at,
                )
            )

        ts = get_current_timestamp()
        snap0 = TurnPostSnapshot(
            turn_post_id="tp_t0",
            run_id=run.run_id,
            turn_number=0,
            author_agent_id=agent_id,
            author_handle_at_time="writer.bsky.social",
            author_display_name_at_time="Writer",
            body_text="t0",
            created_at=ts,
            explanation="e",
            model_used=None,
            generation_metadata_json=None,
            generation_created_at=ts,
        )
        snap1 = TurnPostSnapshot(
            turn_post_id="tp_t1",
            run_id=run.run_id,
            turn_number=1,
            author_agent_id=agent_id,
            author_handle_at_time="writer.bsky.social",
            author_display_name_at_time="Writer",
            body_text="t1",
            created_at=ts,
            explanation="e",
            model_used=None,
            generation_metadata_json=None,
            generation_created_at=ts,
        )
        turn_post_repo.write_turn_posts(run.run_id, 0, [snap0])
        turn_post_repo.write_turn_posts(run.run_id, 1, [snap1])

        assert turn_post_repo.list_turn_posts_for_run_at_turn(run.run_id, 0) == [snap0]
        assert turn_post_repo.list_turn_posts_for_run_at_turn(run.run_id, 1) == [snap1]

        before_0 = turn_post_repo.list_turn_posts_for_run_before_turn(run.run_id, 0)
        assert before_0 == []

        before_1 = turn_post_repo.list_turn_posts_for_run_before_turn(run.run_id, 1)
        assert [s.turn_post_id for s in before_1] == ["tp_t0"]

        before_2 = turn_post_repo.list_turn_posts_for_run_before_turn(run.run_id, 2)
        assert [s.turn_post_id for s in before_2] == ["tp_t0", "tp_t1"]
