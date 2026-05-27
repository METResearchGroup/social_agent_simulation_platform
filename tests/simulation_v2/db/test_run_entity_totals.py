"""Tests for count_run_entity_totals repository method."""

from __future__ import annotations

from pathlib import Path

import pytest

from simulation_v2.db.connection import transaction
from simulation_v2.db.database import SimulationDatabase
from tests.simulation_v2.db import factories


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "test.sqlite3"
    SimulationDatabase(path).initialize()
    return path


class TestCountRunEntityTotals:
    def test_returns_all_contract_keys_for_populated_run(self, db_path: Path) -> None:
        run = factories.RunRecordFactory.create()
        turn = factories.TurnRecordFactory.create(run_id=run.run_id, turn_number=1)
        user = factories.UserRecordFactory.create(run_id=run.run_id)
        post = factories.PostRecordFactory.create(
            run_id=run.run_id, author_id=user.user_id
        )
        like = factories.LikeRecordFactory.create(
            run_id=run.run_id, post_id=post.post_id, author_id=user.user_id
        )
        follow = factories.FollowRecordFactory.create(run_id=run.run_id)
        comment = factories.CommentRecordFactory.create(
            run_id=run.run_id, parent_post_id=post.post_id, author_id=user.user_id
        )
        memory = factories.AgentMemoryRecordFactory.create(
            run_id=run.run_id, user_id=user.user_id
        )
        feed = factories.GeneratedFeedRecordFactory.create(
            run_id=run.run_id, turn_id=turn.turn_id
        )
        generation = factories.GenerationRecordFactory.create(
            run_id=run.run_id, turn_id=turn.turn_id, user_id=user.user_id
        )
        proposed = factories.ProposedActionRecordFactory.create(
            run_id=run.run_id,
            turn_id=turn.turn_id,
            user_id=user.user_id,
            generation_id=generation.generation_id,
        )
        eval_run = factories.EvalRunRecordFactory.create(
            run_id=run.run_id, turn_id=turn.turn_id
        )
        eval_metric = factories.EvalMetricRecordFactory.create(
            run_id=run.run_id,
            turn_id=turn.turn_id,
            eval_run_id=eval_run.eval_run_id,
        )

        db = SimulationDatabase(db_path)
        with transaction(db_path) as conn:
            db.repos.insert_run(run, conn)
            db.repos.insert_turn(turn, conn)
            db.repos.insert_user(user, conn)
            db.repos.insert_post(post, conn)
            db.repos.insert_like(like, conn)
            db.repos.insert_follow(follow, conn)
            db.repos.insert_comment(comment, conn)
            db.repos.insert_agent_memory(memory, conn)
            db.repos.insert_generated_feed(feed, conn)
            db.repos.insert_generation(generation, conn)
            db.repos.insert_proposed_action(proposed, conn)
            db.repos.insert_eval_run(eval_run, conn)
            db.repos.insert_eval_metric(eval_metric, conn)

            totals = db.repos.count_run_entity_totals(run.run_id, conn)

        assert totals == {
            "user_count": 1,
            "post_count": 1,
            "like_count": 1,
            "follow_count": 1,
            "comment_count": 1,
            "memory_count": 1,
            "generation_count": 1,
            "proposed_action_count": 1,
            "generated_feed_count": 1,
            "eval_run_count": 1,
            "eval_metric_count": 1,
            "turn_count": 1,
        }

    def test_returns_zeros_for_empty_run(self, db_path: Path) -> None:
        run = factories.RunRecordFactory.create()
        db = SimulationDatabase(db_path)
        with transaction(db_path) as conn:
            db.repos.insert_run(run, conn)
            totals = db.repos.count_run_entity_totals(run.run_id, conn)

        assert all(value == 0 for value in totals.values())
