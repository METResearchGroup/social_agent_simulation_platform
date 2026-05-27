"""Tests for SimulationRepositories.persist_turn_diffs."""

from __future__ import annotations

from pathlib import Path

import pytest

from simulation_v2.db.connection import transaction
from simulation_v2.db.database import SimulationDatabase
from simulation_v2.worker.state import PendingTurnDiffs
from tests.simulation_v2.db import factories


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "test.sqlite3"
    SimulationDatabase(path).initialize()
    return path


class TestPersistTurnDiffs:
    def test_persists_mixed_entity_diffs(self, db_path: Path) -> None:
        run = factories.RunRecordFactory.create()
        post = factories.PostRecordFactory.create(run_id=run.run_id, post_id="p-new")
        like = factories.LikeRecordFactory.create(run_id=run.run_id, like_id="l-new")
        follow = factories.FollowRecordFactory.create(
            run_id=run.run_id, follow_id="f-new"
        )
        comment = factories.CommentRecordFactory.create(
            run_id=run.run_id, comment_id="c-new"
        )
        diffs = PendingTurnDiffs(
            posts=[post],
            likes=[like],
            follows=[follow],
            comments=[comment],
        )

        db = SimulationDatabase(db_path)
        with transaction(db_path) as conn:
            db.repos.insert_run(run, conn)
            db.repos.persist_turn_diffs(diffs, conn)

            assert len(db.repos.list_posts_for_run(run.run_id, conn)) == 1
            assert len(db.repos.list_likes_for_run(run.run_id, conn)) == 1
            assert len(db.repos.list_follows_for_run(run.run_id, conn)) == 1
            assert len(db.repos.list_comments_for_run(run.run_id, conn)) == 1
            assert db.repos.get_post(run.run_id, "p-new", conn) == post
            assert db.repos.get_like("l-new", conn) == like
            assert db.repos.get_follow("f-new", conn) == follow
            assert db.repos.get_comment("c-new", conn) == comment

    def test_empty_diff_is_no_op(self, db_path: Path) -> None:
        run = factories.RunRecordFactory.create()
        db = SimulationDatabase(db_path)
        with transaction(db_path) as conn:
            db.repos.insert_run(run, conn)
            db.repos.persist_turn_diffs(PendingTurnDiffs(), conn)
            assert db.repos.list_posts_for_run(run.run_id, conn) == []
            assert db.repos.list_likes_for_run(run.run_id, conn) == []
            assert db.repos.list_follows_for_run(run.run_id, conn) == []
            assert db.repos.list_comments_for_run(run.run_id, conn) == []

    def test_persist_memory_diff_updates_agent_memory(self, db_path: Path) -> None:
        run = factories.RunRecordFactory.create()
        turn = factories.TurnRecordFactory.create(run_id=run.run_id, turn_number=1)
        memory = factories.AgentMemoryRecordFactory.create(
            run_id=run.run_id,
            user_id="u1",
            episodic="",
            personalized="",
            social="",
        )
        memory_diff = factories.MemoryDiffRecordFactory.create(
            run_id=run.run_id,
            turn_id=turn.turn_id,
            user_id="u1",
            memory_type="episodic",
            content="Turn 1: liked post p1",
        )
        diffs = PendingTurnDiffs(memory_diffs=[memory_diff])

        db = SimulationDatabase(db_path)
        with transaction(db_path) as conn:
            db.repos.insert_run(run, conn)
            db.repos.insert_turn(turn, conn)
            db.repos.insert_agent_memory(memory, conn)
            db.repos.persist_turn_diffs(diffs, conn)
            loaded = db.repos.get_agent_memory(run.run_id, "u1", conn)
            persisted_diff = db.repos.get_memory_diff(memory_diff.memory_diff_id, conn)

        assert loaded is not None
        assert loaded.episodic == "Turn 1: liked post p1"
        assert persisted_diff == memory_diff
