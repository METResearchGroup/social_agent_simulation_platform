"""Repository constraint and round-trip tests."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from simulation_v2.db.connection import transaction
from simulation_v2.db.database import SimulationDatabase
from tests.simulation_v2.db import factories


@pytest.fixture
def db(tmp_path: Path) -> SimulationDatabase:
    database = SimulationDatabase(tmp_path / "test.sqlite3")
    database.initialize()
    return database


def _insert_run_and_turn(db: SimulationDatabase) -> tuple[str, str]:
    run = factories.RunRecordFactory.create()
    turn = factories.TurnRecordFactory.create(run_id=run.run_id, turn_number=1)
    with transaction(db._db_path) as conn:
        db.repos.insert_run(run, conn)
        db.repos.insert_turn(turn, conn)
    return run.run_id, turn.turn_id


class TestRepositoryRoundTrips:
    def test_run_round_trip(self, db: SimulationDatabase) -> None:
        record = factories.RunRecordFactory.create()
        with transaction(db._db_path) as conn:
            db.repos.insert_run(record, conn)
            loaded = db.repos.get_run(record.run_id, conn)

        assert loaded == record

    def test_turn_round_trip(self, db: SimulationDatabase) -> None:
        run = factories.RunRecordFactory.create()
        turn = factories.TurnRecordFactory.create(run_id=run.run_id)
        with transaction(db._db_path) as conn:
            db.repos.insert_run(run, conn)
            db.repos.insert_turn(turn, conn)
            loaded = db.repos.get_turn(turn.turn_id, conn)

        assert loaded == turn

    def test_user_round_trip(self, db: SimulationDatabase) -> None:
        run_id, _ = _insert_run_and_turn(db)
        record = factories.UserRecordFactory.create(run_id=run_id)
        with transaction(db._db_path) as conn:
            db.repos.insert_user(record, conn)
            loaded = db.repos.get_user(run_id, record.user_id, conn)

        assert loaded == record

    def test_post_round_trip(self, db: SimulationDatabase) -> None:
        run_id, _ = _insert_run_and_turn(db)
        record = factories.PostRecordFactory.create(run_id=run_id)
        with transaction(db._db_path) as conn:
            db.repos.insert_post(record, conn)
            loaded = db.repos.get_post(run_id, record.post_id, conn)

        assert loaded == record

    def test_like_round_trip(self, db: SimulationDatabase) -> None:
        run_id, _ = _insert_run_and_turn(db)
        record = factories.LikeRecordFactory.create(run_id=run_id)
        with transaction(db._db_path) as conn:
            db.repos.insert_like(record, conn)
            loaded = db.repos.get_like(record.like_id, conn)

        assert loaded == record

    def test_follow_round_trip(self, db: SimulationDatabase) -> None:
        run_id, _ = _insert_run_and_turn(db)
        record = factories.FollowRecordFactory.create(run_id=run_id)
        with transaction(db._db_path) as conn:
            db.repos.insert_follow(record, conn)
            loaded = db.repos.get_follow(record.follow_id, conn)

        assert loaded == record

    def test_comment_round_trip(self, db: SimulationDatabase) -> None:
        run_id, _ = _insert_run_and_turn(db)
        record = factories.CommentRecordFactory.create(run_id=run_id)
        with transaction(db._db_path) as conn:
            db.repos.insert_comment(record, conn)
            loaded = db.repos.get_comment(record.comment_id, conn)

        assert loaded == record

    def test_agent_memory_round_trip(self, db: SimulationDatabase) -> None:
        run_id, _ = _insert_run_and_turn(db)
        record = factories.AgentMemoryRecordFactory.create(run_id=run_id)
        with transaction(db._db_path) as conn:
            db.repos.insert_agent_memory(record, conn)
            loaded = db.repos.get_agent_memory(run_id, record.user_id, conn)

        assert loaded == record

    def test_memory_diff_round_trip(self, db: SimulationDatabase) -> None:
        run_id, turn_id = _insert_run_and_turn(db)
        record = factories.MemoryDiffRecordFactory.create(
            run_id=run_id, turn_id=turn_id
        )
        with transaction(db._db_path) as conn:
            db.repos.insert_memory_diff(record, conn)
            loaded = db.repos.get_memory_diff(record.memory_diff_id, conn)

        assert loaded == record

    def test_generated_feed_round_trip(self, db: SimulationDatabase) -> None:
        run_id, turn_id = _insert_run_and_turn(db)
        record = factories.GeneratedFeedRecordFactory.create(
            run_id=run_id, turn_id=turn_id
        )
        with transaction(db._db_path) as conn:
            db.repos.insert_generated_feed(record, conn)
            loaded = db.repos.get_generated_feed(record.feed_id, conn)

        assert loaded == record

    def test_generation_round_trip(self, db: SimulationDatabase) -> None:
        run_id, turn_id = _insert_run_and_turn(db)
        record = factories.GenerationRecordFactory.create(
            run_id=run_id, turn_id=turn_id
        )
        with transaction(db._db_path) as conn:
            db.repos.insert_generation(record, conn)
            loaded = db.repos.get_generation(record.generation_id, conn)

        assert loaded == record

    def test_llm_proposed_action_round_trip(self, db: SimulationDatabase) -> None:
        run_id, turn_id = _insert_run_and_turn(db)
        generation = factories.GenerationRecordFactory.create(
            run_id=run_id, turn_id=turn_id
        )
        record = factories.LlmProposedActionRecordFactory.create(
            run_id=run_id,
            turn_id=turn_id,
            generation_id=generation.generation_id,
        )
        with transaction(db._db_path) as conn:
            db.repos.insert_generation(generation, conn)
            db.repos.insert_llm_proposed_action(record, conn)
            loaded = db.repos.get_llm_proposed_action(
                record.llm_proposed_action_id, conn
            )

        assert loaded == record

    def test_proposed_action_round_trip(self, db: SimulationDatabase) -> None:
        run_id, turn_id = _insert_run_and_turn(db)
        generation = factories.GenerationRecordFactory.create(
            run_id=run_id, turn_id=turn_id
        )
        record = factories.ProposedActionRecordFactory.create(
            run_id=run_id,
            turn_id=turn_id,
            generation_id=generation.generation_id,
        )
        with transaction(db._db_path) as conn:
            db.repos.insert_generation(generation, conn)
            db.repos.insert_proposed_action(record, conn)
            loaded = db.repos.get_proposed_action(record.action_id, conn)

        assert loaded == record

    def test_eval_run_round_trip(self, db: SimulationDatabase) -> None:
        run_id, turn_id = _insert_run_and_turn(db)
        record = factories.EvalRunRecordFactory.create(run_id=run_id, turn_id=turn_id)
        with transaction(db._db_path) as conn:
            db.repos.insert_eval_run(record, conn)
            loaded = db.repos.get_eval_run(record.eval_run_id, conn)

        assert loaded == record

    def test_eval_metric_round_trip(self, db: SimulationDatabase) -> None:
        run_id, turn_id = _insert_run_and_turn(db)
        eval_run = factories.EvalRunRecordFactory.create(run_id=run_id, turn_id=turn_id)
        record = factories.EvalMetricRecordFactory.create(
            run_id=run_id,
            turn_id=turn_id,
            eval_run_id=eval_run.eval_run_id,
        )
        with transaction(db._db_path) as conn:
            db.repos.insert_eval_run(eval_run, conn)
            db.repos.insert_eval_metric(record, conn)
            loaded = db.repos.get_eval_metric(record.eval_metric_id, conn)

        assert loaded == record


class TestRepositoryConstraints:
    def test_duplicate_turn_raises(self, db: SimulationDatabase) -> None:
        run = factories.RunRecordFactory.create()
        turn_a = factories.TurnRecordFactory.create(run_id=run.run_id, turn_number=1)
        turn_b = factories.TurnRecordFactory.create(run_id=run.run_id, turn_number=1)

        with transaction(db._db_path) as conn:
            db.repos.insert_run(run, conn)
            db.repos.insert_turn(turn_a, conn)
            with pytest.raises(sqlite3.IntegrityError):
                db.repos.insert_turn(turn_b, conn)

    def test_duplicate_user_raises(self, db: SimulationDatabase) -> None:
        run_id, _ = _insert_run_and_turn(db)
        user_a = factories.UserRecordFactory.create(run_id=run_id, user_id="u1")
        user_b = factories.UserRecordFactory.create(run_id=run_id, user_id="u1")

        with transaction(db._db_path) as conn:
            db.repos.insert_user(user_a, conn)
            with pytest.raises(sqlite3.IntegrityError):
                db.repos.insert_user(user_b, conn)

    def test_duplicate_post_raises(self, db: SimulationDatabase) -> None:
        run_id, _ = _insert_run_and_turn(db)
        post_a = factories.PostRecordFactory.create(run_id=run_id, post_id="p1")
        post_b = factories.PostRecordFactory.create(run_id=run_id, post_id="p1")

        with transaction(db._db_path) as conn:
            db.repos.insert_post(post_a, conn)
            with pytest.raises(sqlite3.IntegrityError):
                db.repos.insert_post(post_b, conn)

    def test_duplicate_like_raises(self, db: SimulationDatabase) -> None:
        run_id, _ = _insert_run_and_turn(db)
        like_a = factories.LikeRecordFactory.create(
            run_id=run_id, author_id="u1", post_id="p1"
        )
        like_b = factories.LikeRecordFactory.create(
            run_id=run_id, author_id="u1", post_id="p1"
        )

        with transaction(db._db_path) as conn:
            db.repos.insert_like(like_a, conn)
            with pytest.raises(sqlite3.IntegrityError):
                db.repos.insert_like(like_b, conn)

    def test_duplicate_follow_raises(self, db: SimulationDatabase) -> None:
        run_id, _ = _insert_run_and_turn(db)
        follow_a = factories.FollowRecordFactory.create(
            run_id=run_id, follower_id="u1", followee_id="u2"
        )
        follow_b = factories.FollowRecordFactory.create(
            run_id=run_id, follower_id="u1", followee_id="u2"
        )

        with transaction(db._db_path) as conn:
            db.repos.insert_follow(follow_a, conn)
            with pytest.raises(sqlite3.IntegrityError):
                db.repos.insert_follow(follow_b, conn)

    def test_duplicate_memory_raises(self, db: SimulationDatabase) -> None:
        run_id, _ = _insert_run_and_turn(db)
        memory_a = factories.AgentMemoryRecordFactory.create(
            run_id=run_id, user_id="u1"
        )
        memory_b = factories.AgentMemoryRecordFactory.create(
            run_id=run_id, user_id="u1"
        )

        with transaction(db._db_path) as conn:
            db.repos.insert_agent_memory(memory_a, conn)
            with pytest.raises(sqlite3.IntegrityError):
                db.repos.insert_agent_memory(memory_b, conn)

    def test_duplicate_feed_raises(self, db: SimulationDatabase) -> None:
        run_id, turn_id = _insert_run_and_turn(db)
        feed_a = factories.GeneratedFeedRecordFactory.create(
            run_id=run_id, turn_id=turn_id, user_id="u1"
        )
        feed_b = factories.GeneratedFeedRecordFactory.create(
            run_id=run_id, turn_id=turn_id, user_id="u1"
        )

        with transaction(db._db_path) as conn:
            db.repos.insert_generated_feed(feed_a, conn)
            with pytest.raises(sqlite3.IntegrityError):
                db.repos.insert_generated_feed(feed_b, conn)

    def test_foreign_key_turn_requires_run(self, db: SimulationDatabase) -> None:
        turn = factories.TurnRecordFactory.create(run_id="missing-run")

        with transaction(db._db_path) as conn:
            with pytest.raises(sqlite3.IntegrityError):
                db.repos.insert_turn(turn, conn)
