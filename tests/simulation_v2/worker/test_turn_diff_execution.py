"""Integration tests for turn diff execution after validation."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from simulation_v2.actions.models import (
    LlmGenerationResult,
    LlmLikePostOutput,
    LlmWritePostOutput,
)
from simulation_v2.config import ActionConfig, FeedConfig, LocalSimulationConfig
from simulation_v2.db.connection import transaction
from simulation_v2.db.database import SimulationDatabase
from simulation_v2.memory.service import fetch_memory_for_prompt
from simulation_v2.seed.loader import persist_seed_for_run
from simulation_v2.seed.models import LoadedPostModel, LoadedUserModel, SeedDataset
from simulation_v2.worker.state import load_turn_snapshot
from simulation_v2.worker.turn_executor import execute_turn
from tests.simulation_v2.actions.test_action_service import _tiny_dataset
from tests.simulation_v2.db import factories

FIXED_TS = "2026-01-01T00:00:00.000000+00:00"


def _like_config(*, total_turns: int = 1) -> LocalSimulationConfig:
    return LocalSimulationConfig.default().model_copy(
        update={
            "total_turns": total_turns,
            "feed": FeedConfig(include_probability=1.0, max_posts=10),
            "action": ActionConfig(
                enable_like_post=True,
                enable_write_post=False,
                enable_follow_user=False,
                enable_comment_on_post=False,
            ),
        }
    )


def _write_post_config(*, total_turns: int = 2) -> LocalSimulationConfig:
    return LocalSimulationConfig.default().model_copy(
        update={
            "total_turns": total_turns,
            "feed": FeedConfig(include_probability=1.0, max_posts=10),
            "action": ActionConfig(
                enable_like_post=False,
                enable_write_post=True,
                enable_follow_user=False,
                enable_comment_on_post=False,
            ),
        }
    )


class TestTurnDiffExecution:
    def test_single_turn_executes_validated_like(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.sqlite3"
        db = SimulationDatabase(db_path)
        db.initialize()
        config = _like_config()
        run = factories.RunRecordFactory.create(
            config_json=config.model_dump(mode="json"),
            seed_metadata_json=None,
        )
        dataset = _tiny_dataset()
        mock_result = LlmGenerationResult(
            status="completed",
            parsed=LlmLikePostOutput(post_ids=["p2"]),
            latency_ms=1.0,
        )

        with transaction(db_path) as conn:
            db.repos.insert_run(run, conn)
            persist_seed_for_run(run.run_id, dataset, db.repos, conn)
            likes_before = len(db.repos.list_likes_for_run(run.run_id, conn))

        with patch(
            "simulation_v2.actions.service.invoke_structured_generation",
            return_value=mock_result,
        ):
            with transaction(db_path) as conn:
                execute_turn(run.run_id, 1, config, conn, db.repos)

        with transaction(db_path) as conn:
            likes = db.repos.list_likes_for_run(run.run_id, conn)

        assert len(likes) == likes_before + 1
        new_like = next(
            like for like in likes if like.author_id == "u1" and like.post_id == "p2"
        )
        assert new_like.created_at_turn == 1

    def test_turn_two_reads_turn_one_write_post(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.sqlite3"
        db = SimulationDatabase(db_path)
        db.initialize()
        config = _write_post_config(total_turns=2)
        run = factories.RunRecordFactory.create(
            config_json=config.model_dump(mode="json"),
            seed_metadata_json=None,
        )
        dataset = SeedDataset(
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
            },
            posts={
                "p1": LoadedPostModel(
                    post_id="p1",
                    user_id="u1",
                    content="seed",
                    created_at=FIXED_TS,
                    num_likes=0,
                ),
            },
            likes={},
            follows={},
        )
        write_result = LlmGenerationResult(
            status="completed",
            parsed=LlmWritePostOutput(content="turn one post"),
            latency_ms=1.0,
        )

        with transaction(db_path) as conn:
            db.repos.insert_run(run, conn)
            persist_seed_for_run(run.run_id, dataset, db.repos, conn)

        with patch(
            "simulation_v2.actions.service.invoke_structured_generation",
            return_value=write_result,
        ):
            with transaction(db_path) as conn:
                execute_turn(run.run_id, 1, config, conn, db.repos)

        with transaction(db_path) as conn:
            posts_after_turn_one = db.repos.list_posts_for_run(run.run_id, conn)
            turn_one_posts = [
                post
                for post in posts_after_turn_one
                if post.content == "turn one post" and post.created_at_turn == 1
            ]
            assert len(turn_one_posts) == 1
            turn_one_post_id = turn_one_posts[0].post_id

        with patch(
            "simulation_v2.actions.service.invoke_structured_generation",
            return_value=write_result,
        ):
            with transaction(db_path) as conn:
                execute_turn(run.run_id, 2, config, conn, db.repos)
                turns = db.repos.list_turns_for_run(run.run_id, conn)
                turn_two = next(t for t in turns if t.turn_number == 2)
                snapshot = load_turn_snapshot(
                    run.run_id, turn_two.turn_id, db.repos, conn
                )

        assert turn_one_post_id in snapshot.posts
        assert snapshot.posts[turn_one_post_id].content == "turn one post"

    def test_turn_two_reads_turn_one_memory_update(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.sqlite3"
        db = SimulationDatabase(db_path)
        db.initialize()
        config = _write_post_config(total_turns=2)
        run = factories.RunRecordFactory.create(
            config_json=config.model_dump(mode="json"),
            seed_metadata_json=None,
        )
        dataset = SeedDataset(
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
            },
            posts={
                "p1": LoadedPostModel(
                    post_id="p1",
                    user_id="u1",
                    content="seed",
                    created_at=FIXED_TS,
                    num_likes=0,
                ),
            },
            likes={},
            follows={},
        )
        write_result = LlmGenerationResult(
            status="completed",
            parsed=LlmWritePostOutput(content="turn one post"),
            latency_ms=1.0,
        )

        with transaction(db_path) as conn:
            db.repos.insert_run(run, conn)
            persist_seed_for_run(run.run_id, dataset, db.repos, conn)

        with patch(
            "simulation_v2.actions.service.invoke_structured_generation",
            return_value=write_result,
        ):
            with transaction(db_path) as conn:
                execute_turn(run.run_id, 1, config, conn, db.repos)

        with transaction(db_path) as conn:
            memory = db.repos.get_agent_memory(run.run_id, "u1", conn)
            assert memory is not None
            assert 'wrote post "turn one post"' in (memory.episodic or "")
            assert memory.personalized is not None
            assert 'posted "turn one post"' in memory.personalized

        with patch(
            "simulation_v2.actions.service.invoke_structured_generation",
            return_value=write_result,
        ):
            with transaction(db_path) as conn:
                execute_turn(run.run_id, 2, config, conn, db.repos)
                turns = db.repos.list_turns_for_run(run.run_id, conn)
                turn_two = next(t for t in turns if t.turn_number == 2)
                snapshot = load_turn_snapshot(
                    run.run_id, turn_two.turn_id, db.repos, conn
                )

        u1_memory = snapshot.agent_memories["u1"]
        assert 'wrote post "turn one post"' in (u1_memory.episodic or "")
        prompt_text = fetch_memory_for_prompt(u1_memory)
        assert 'wrote post "turn one post"' in prompt_text

    def test_rejected_actions_do_not_persist_likes(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.sqlite3"
        db = SimulationDatabase(db_path)
        db.initialize()
        config = _like_config()
        run = factories.RunRecordFactory.create(
            config_json=config.model_dump(mode="json"),
            seed_metadata_json=None,
        )
        dataset = SeedDataset(
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
            },
            posts={
                "p1": LoadedPostModel(
                    post_id="p1",
                    user_id="u1",
                    content="solo",
                    created_at=FIXED_TS,
                    num_likes=0,
                ),
            },
            likes={},
            follows={},
        )
        mock_result = LlmGenerationResult(
            status="completed",
            parsed=LlmLikePostOutput(post_ids=["missing-post"]),
            latency_ms=1.0,
        )

        with transaction(db_path) as conn:
            db.repos.insert_run(run, conn)
            persist_seed_for_run(run.run_id, dataset, db.repos, conn)
            likes_before = len(db.repos.list_likes_for_run(run.run_id, conn))

        with patch(
            "simulation_v2.actions.service.invoke_structured_generation",
            return_value=mock_result,
        ):
            with transaction(db_path) as conn:
                execute_turn(run.run_id, 1, config, conn, db.repos)

        with transaction(db_path) as conn:
            likes_after = db.repos.list_likes_for_run(run.run_id, conn)

        assert len(likes_after) == likes_before
