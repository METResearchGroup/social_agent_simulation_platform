"""Tests for run-scoped repository list helpers used by turn snapshots."""

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


class TestListEntitiesForRun:
    def test_list_methods_return_inserted_records_for_run(self, db_path: Path) -> None:
        run = factories.RunRecordFactory.create()
        other_run = factories.RunRecordFactory.create()
        user = factories.UserRecordFactory.create(run_id=run.run_id, user_id="u1")
        post = factories.PostRecordFactory.create(
            run_id=run.run_id, post_id="p1", author_id="u1", created_at_turn=0
        )
        like = factories.LikeRecordFactory.create(
            run_id=run.run_id,
            like_id="l1",
            post_id="p1",
            author_id="u1",
            created_at_turn=0,
        )
        follow = factories.FollowRecordFactory.create(
            run_id=run.run_id,
            follow_id="f1",
            follower_id="u1",
            followee_id="u2",
            created_at_turn=0,
        )
        comment = factories.CommentRecordFactory.create(
            run_id=run.run_id,
            comment_id="c1",
            parent_post_id="p1",
            author_id="u1",
            created_at_turn=0,
        )
        memory = factories.AgentMemoryRecordFactory.create(
            run_id=run.run_id, user_id="u1"
        )
        turn = factories.TurnRecordFactory.create(run_id=run.run_id, turn_number=1)
        feed = factories.GeneratedFeedRecordFactory.create(
            run_id=run.run_id, turn_id=turn.turn_id
        )
        other_user = factories.UserRecordFactory.create(run_id=other_run.run_id)

        db = SimulationDatabase(db_path)
        with transaction(db_path) as conn:
            db.repos.insert_run(run, conn)
            db.repos.insert_run(other_run, conn)
            db.repos.insert_user(user, conn)
            db.repos.insert_user(other_user, conn)
            db.repos.insert_post(post, conn)
            db.repos.insert_like(like, conn)
            db.repos.insert_follow(follow, conn)
            db.repos.insert_comment(comment, conn)
            db.repos.insert_agent_memory(memory, conn)
            db.repos.insert_turn(turn, conn)
            db.repos.insert_generated_feed(feed, conn)

            users = db.repos.list_users_for_run(run.run_id, conn)
            posts = db.repos.list_posts_for_run(run.run_id, conn)
            likes = db.repos.list_likes_for_run(run.run_id, conn)
            follows = db.repos.list_follows_for_run(run.run_id, conn)
            comments = db.repos.list_comments_for_run(run.run_id, conn)
            memories = db.repos.list_agent_memories_for_run(run.run_id, conn)
            feeds = db.repos.list_generated_feeds_for_run(run.run_id, conn)

        assert users == [user]
        assert posts == [post]
        assert likes == [like]
        assert follows == [follow]
        assert comments == [comment]
        assert memories == [memory]
        assert feeds == [feed]
