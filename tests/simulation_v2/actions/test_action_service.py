"""Integration tests for action LLM generation persistence."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from simulation_v2.actions.models import LlmGenerationResult, LlmLikePostOutput
from simulation_v2.actions.service import (
    generate_and_persist_llm_actions,
    validate_and_persist_proposed_actions,
)
from simulation_v2.config import ActionConfig, FeedConfig, LocalSimulationConfig
from simulation_v2.db.connection import transaction
from simulation_v2.db.database import SimulationDatabase
from simulation_v2.feeds.service import generate_and_persist_feeds
from simulation_v2.models.seed_data import LoadedPostModel, LoadedUserModel
from simulation_v2.seed.loader import persist_seed_for_run
from simulation_v2.seed.models import SeedDataset
from simulation_v2.worker.state import load_turn_snapshot
from simulation_v2.worker.turn_executor import execute_turn
from tests.simulation_v2.db import factories

FIXED_TS = "2026-01-01T00:00:00.000000+00:00"


def _tiny_dataset() -> SeedDataset:
    return SeedDataset(
        users={
            "u1": LoadedUserModel(
                user_id="u1",
                name="Alice",
                email="a@example.com",
                username="alice",
                created_at=FIXED_TS,
                num_followers=0,
                num_follows=0,
            ),
            "u2": LoadedUserModel(
                user_id="u2",
                name="Bob",
                email="b@example.com",
                username="bob",
                created_at=FIXED_TS,
                num_followers=0,
                num_follows=0,
            ),
        },
        posts={
            "p1": LoadedPostModel(
                post_id="p1",
                user_id="u1",
                content="hello",
                created_at=FIXED_TS,
                num_likes=1,
            ),
            "p2": LoadedPostModel(
                post_id="p2",
                user_id="u2",
                content="world",
                created_at=FIXED_TS,
                num_likes=0,
            ),
        },
        likes={},
        follows={},
    )


class TestGenerateAndPersistLlmActions:
    def test_persists_generation_and_llm_proposed_actions(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.sqlite3"
        db = SimulationDatabase(db_path)
        db.initialize()
        config = LocalSimulationConfig.default().model_copy(
            update={
                "feed": FeedConfig(include_probability=1.0, max_posts=10),
                "action": ActionConfig(
                    enable_like_post=True,
                    enable_write_post=False,
                    enable_follow_user=False,
                    enable_comment_on_post=False,
                ),
            }
        )
        run = factories.RunRecordFactory.create(
            config_json=config.model_dump(mode="json"),
            seed_metadata_json=None,
        )
        dataset = _tiny_dataset()

        mock_result = LlmGenerationResult(
            status="completed",
            parsed=LlmLikePostOutput(post_ids=["p2"]),
            latency_ms=12.5,
            prompt_tokens=10,
            completion_tokens=5,
            raw_response_json={"post_ids": ["p2"]},
        )

        with transaction(db_path) as conn:
            db.repos.insert_run(run, conn)
            persist_seed_for_run(run.run_id, dataset, db.repos, conn)
            turn = factories.TurnRecordFactory.create(
                run_id=run.run_id,
                turn_number=1,
                status="pending",
            )
            db.repos.insert_turn(turn, conn)
            snapshot = load_turn_snapshot(run.run_id, turn.turn_id, db.repos, conn)
            feed_records = generate_and_persist_feeds(
                snapshot,
                config.feed,
                db.repos,
                conn,
            )

            with patch(
                "simulation_v2.actions.service.invoke_structured_generation",
                return_value=mock_result,
            ) as mock_invoke:
                generations = generate_and_persist_llm_actions(
                    snapshot,
                    feed_records,
                    config.action,
                    config.llm,
                    db.repos,
                    conn,
                )
                validate_and_persist_proposed_actions(
                    snapshot,
                    feed_records,
                    config.action,
                    db.repos,
                    conn,
                )

        assert mock_invoke.call_count == 2
        assert len(generations) == 2
        assert all(gen.status == "completed" for gen in generations)
        assert all(gen.action_type == "like_post" for gen in generations)

        with transaction(db_path) as conn:
            loaded_generations = db.repos.list_generations_for_turn(
                run.run_id, turn.turn_id, conn
            )
            loaded_actions = db.repos.list_llm_proposed_actions_for_turn(
                run.run_id, turn.turn_id, conn
            )
            proposed_actions = db.repos.list_proposed_actions_for_turn(
                run.run_id, turn.turn_id, conn
            )

        assert len(loaded_generations) == 2
        assert len(loaded_actions) == 2
        assert {action.generation_id for action in loaded_actions} == {
            gen.generation_id for gen in loaded_generations
        }
        assert all(action.action_type == "like_post" for action in loaded_actions)
        assert all(action.target_id == "p2" for action in loaded_actions)
        assert len(proposed_actions) == 2
        validated = [action for action in proposed_actions if action.user_id == "u1"]
        rejected = [action for action in proposed_actions if action.user_id == "u2"]
        assert len(validated) == 1
        assert validated[0].record_kind == "validated"
        assert validated[0].target_id == "p2"
        assert len(rejected) == 1
        assert rejected[0].record_kind == "rejected"
        assert rejected[0].filter_id == "missing_target_post"

    def test_persists_failed_generation_without_proposed_actions(
        self, tmp_path: Path
    ) -> None:
        db_path = tmp_path / "test.sqlite3"
        db = SimulationDatabase(db_path)
        db.initialize()
        config = LocalSimulationConfig.default().model_copy(
            update={
                "feed": FeedConfig(include_probability=1.0, max_posts=10),
                "action": ActionConfig(
                    enable_like_post=True,
                    enable_write_post=False,
                    enable_follow_user=False,
                    enable_comment_on_post=False,
                ),
            }
        )
        run = factories.RunRecordFactory.create(
            config_json=config.model_dump(mode="json"),
            seed_metadata_json=None,
        )
        dataset = _tiny_dataset()

        failed_result = LlmGenerationResult(
            status="failed",
            error="provider down",
            latency_ms=1.0,
        )

        with transaction(db_path) as conn:
            db.repos.insert_run(run, conn)
            persist_seed_for_run(run.run_id, dataset, db.repos, conn)
            turn = factories.TurnRecordFactory.create(
                run_id=run.run_id,
                turn_number=1,
                status="pending",
            )
            db.repos.insert_turn(turn, conn)
            snapshot = load_turn_snapshot(run.run_id, turn.turn_id, db.repos, conn)
            feed_records = generate_and_persist_feeds(
                snapshot,
                config.feed,
                db.repos,
                conn,
            )

            with patch(
                "simulation_v2.actions.service.invoke_structured_generation",
                return_value=failed_result,
            ):
                generate_and_persist_llm_actions(
                    snapshot,
                    feed_records,
                    config.action,
                    config.llm,
                    db.repos,
                    conn,
                )

        with transaction(db_path) as conn:
            loaded_generations = db.repos.list_generations_for_turn(
                run.run_id, turn.turn_id, conn
            )
            loaded_actions = db.repos.list_llm_proposed_actions_for_turn(
                run.run_id, turn.turn_id, conn
            )
            proposed_actions = db.repos.list_proposed_actions_for_turn(
                run.run_id, turn.turn_id, conn
            )

        assert len(loaded_generations) == 2
        assert all(gen.status == "failed" for gen in loaded_generations)
        assert loaded_actions == []
        assert proposed_actions == []


class TestExecuteTurnActionValidation:
    def test_turn_executor_persists_proposed_actions(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.sqlite3"
        db = SimulationDatabase(db_path)
        db.initialize()
        config = LocalSimulationConfig.default().model_copy(
            update={
                "total_turns": 1,
                "feed": FeedConfig(include_probability=1.0, max_posts=10),
                "action": ActionConfig(
                    enable_like_post=True,
                    enable_write_post=False,
                    enable_follow_user=False,
                    enable_comment_on_post=False,
                ),
            }
        )
        run = factories.RunRecordFactory.create(
            config_json=config.model_dump(mode="json"),
            seed_metadata_json=None,
        )
        dataset = _tiny_dataset()

        mock_result = LlmGenerationResult(
            status="completed",
            parsed=LlmLikePostOutput(post_ids=["p2"]),
            latency_ms=12.5,
            prompt_tokens=10,
            completion_tokens=5,
            raw_response_json={"post_ids": ["p2"]},
        )

        with transaction(db_path) as conn:
            db.repos.insert_run(run, conn)
            persist_seed_for_run(run.run_id, dataset, db.repos, conn)

        with patch(
            "simulation_v2.actions.service.invoke_structured_generation",
            return_value=mock_result,
        ):
            with transaction(db_path) as conn:
                execute_turn(run.run_id, 1, config, conn, db.repos)

        with transaction(db_path) as conn:
            turns = db.repos.list_turns_for_run(run.run_id, conn)
            proposed_actions = db.repos.list_proposed_actions_for_turn(
                run.run_id, turns[0].turn_id, conn
            )

        assert len(proposed_actions) == 2
        validated = [action for action in proposed_actions if action.user_id == "u1"]
        rejected = [action for action in proposed_actions if action.user_id == "u2"]
        assert len(validated) == 1
        assert validated[0].record_kind == "validated"
        assert validated[0].target_id == "p2"
        assert len(rejected) == 1
        assert rejected[0].record_kind == "rejected"
        assert rejected[0].filter_id == "missing_target_post"
