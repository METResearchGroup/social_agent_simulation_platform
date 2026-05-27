"""Shared fixtures for simulation_v2 eval plugin tests."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from simulation_v2.db.connection import transaction
from simulation_v2.db.database import SimulationDatabase
from tests.simulation_v2.db import factories


@dataclass(frozen=True)
class EvalFixture:
    db_path: Path
    run_id: str
    turn_id: str
    turn_number: int


def seed_eval_fixture_db(db_path: Path) -> EvalFixture:
    """Insert a run with representative rows for all four eval plugins."""
    db = SimulationDatabase(db_path)
    db.initialize()

    run = factories.RunRecordFactory.create()
    turn = factories.TurnRecordFactory.create(
        run_id=run.run_id, turn_number=1, status="completed"
    )

    user_healthy = factories.UserRecordFactory.create(run_id=run.run_id)
    user_empty = factories.UserRecordFactory.create(run_id=run.run_id)
    user_duplicate = factories.UserRecordFactory.create(run_id=run.run_id)
    user_self = factories.UserRecordFactory.create(run_id=run.run_id)
    user_missing = factories.UserRecordFactory.create(run_id=run.run_id)

    author_other = factories.UserRecordFactory.create(run_id=run.run_id)
    post_a = factories.PostRecordFactory.create(
        run_id=run.run_id,
        author_id=author_other.user_id,
        created_at_turn=0,
    )
    post_b = factories.PostRecordFactory.create(
        run_id=run.run_id,
        author_id=author_other.user_id,
        created_at_turn=0,
    )
    post_self = factories.PostRecordFactory.create(
        run_id=run.run_id,
        author_id=user_self.user_id,
        created_at_turn=0,
    )

    gen_like_1 = factories.GenerationRecordFactory.create(
        run_id=run.run_id,
        turn_id=turn.turn_id,
        user_id=user_healthy.user_id,
        action_type="like_post",
        status="completed",
    )
    gen_like_2 = factories.GenerationRecordFactory.create(
        run_id=run.run_id,
        turn_id=turn.turn_id,
        user_id=user_healthy.user_id,
        action_type="like_post",
        status="completed",
    )
    gen_like_schema_fail = factories.GenerationRecordFactory.create(
        run_id=run.run_id,
        turn_id=turn.turn_id,
        user_id=user_empty.user_id,
        action_type="like_post",
        status="schema_failed",
    )
    gen_write_fail = factories.GenerationRecordFactory.create(
        run_id=run.run_id,
        turn_id=turn.turn_id,
        user_id=user_empty.user_id,
        action_type="write_post",
        status="failed",
    )
    gen_follow = factories.GenerationRecordFactory.create(
        run_id=run.run_id,
        turn_id=turn.turn_id,
        user_id=user_healthy.user_id,
        action_type="follow_user",
        status="completed",
    )
    gen_like_rejected = factories.GenerationRecordFactory.create(
        run_id=run.run_id,
        turn_id=turn.turn_id,
        user_id=user_empty.user_id,
        action_type="like_post",
        status="failed",
    )

    proposed_like_valid_1 = factories.ProposedActionRecordFactory.create(
        run_id=run.run_id,
        turn_id=turn.turn_id,
        user_id=user_healthy.user_id,
        action_type="like_post",
        record_kind="validated",
        generation_id=gen_like_1.generation_id,
        target_id=post_a.post_id,
    )
    proposed_like_valid_2 = factories.ProposedActionRecordFactory.create(
        run_id=run.run_id,
        turn_id=turn.turn_id,
        user_id=user_healthy.user_id,
        action_type="like_post",
        record_kind="validated",
        generation_id=gen_like_2.generation_id,
        target_id=post_b.post_id,
    )
    proposed_like_rejected = factories.ProposedActionRecordFactory.create(
        run_id=run.run_id,
        turn_id=turn.turn_id,
        user_id=user_empty.user_id,
        action_type="like_post",
        record_kind="rejected",
        generation_id=gen_like_rejected.generation_id,
        filter_id="duplicate_like",
        filter_reason="Already liked this post",
        target_id=post_a.post_id,
    )
    proposed_follow_valid = factories.ProposedActionRecordFactory.create(
        run_id=run.run_id,
        turn_id=turn.turn_id,
        user_id=user_healthy.user_id,
        action_type="follow_user",
        record_kind="validated",
        generation_id=gen_follow.generation_id,
        target_id=author_other.user_id,
    )

    like_1 = factories.LikeRecordFactory.create(
        run_id=run.run_id,
        post_id=post_a.post_id,
        author_id=user_healthy.user_id,
        created_at_turn=turn.turn_number,
    )
    like_2 = factories.LikeRecordFactory.create(
        run_id=run.run_id,
        post_id=post_b.post_id,
        author_id=user_healthy.user_id,
        created_at_turn=turn.turn_number,
    )
    follow_1 = factories.FollowRecordFactory.create(
        run_id=run.run_id,
        follower_id=user_healthy.user_id,
        followee_id=author_other.user_id,
        created_at_turn=turn.turn_number,
    )

    healthy_post = factories.FeedPostViewFactory.create(
        post_id=post_a.post_id,
        author_id=author_other.user_id,
    )
    duplicate_post = factories.FeedPostViewFactory.create(
        post_id="dup-post-id",
        author_id=author_other.user_id,
    )
    self_post_view = factories.FeedPostViewFactory.create(
        post_id=post_self.post_id,
        author_id=user_self.user_id,
    )

    feed_healthy = factories.GeneratedFeedRecordFactory.create(
        run_id=run.run_id,
        turn_id=turn.turn_id,
        user_id=user_healthy.user_id,
        feed_post_ids=[healthy_post.post_id],
        feed_posts=[healthy_post],
    )
    feed_empty = factories.GeneratedFeedRecordFactory.create(
        run_id=run.run_id,
        turn_id=turn.turn_id,
        user_id=user_empty.user_id,
        feed_post_ids=[],
        feed_posts=[],
    )
    feed_duplicate = factories.GeneratedFeedRecordFactory.create(
        run_id=run.run_id,
        turn_id=turn.turn_id,
        user_id=user_duplicate.user_id,
        feed_post_ids=[duplicate_post.post_id, duplicate_post.post_id],
        feed_posts=[duplicate_post, duplicate_post],
    )
    feed_self = factories.GeneratedFeedRecordFactory.create(
        run_id=run.run_id,
        turn_id=turn.turn_id,
        user_id=user_self.user_id,
        feed_post_ids=[self_post_view.post_id],
        feed_posts=[self_post_view],
    )
    author_feed_post = factories.FeedPostViewFactory.create(
        post_id=post_b.post_id,
        author_id=user_healthy.user_id,
    )
    feed_author = factories.GeneratedFeedRecordFactory.create(
        run_id=run.run_id,
        turn_id=turn.turn_id,
        user_id=author_other.user_id,
        feed_post_ids=[author_feed_post.post_id],
        feed_posts=[author_feed_post],
    )

    with transaction(db_path) as conn:
        db.repos.insert_run(run, conn)
        db.repos.insert_turn(turn, conn)
        for user in (
            user_healthy,
            user_empty,
            user_duplicate,
            user_self,
            user_missing,
            author_other,
        ):
            db.repos.insert_user(user, conn)
        for post in (post_a, post_b, post_self):
            db.repos.insert_post(post, conn)
        for generation in (
            gen_like_1,
            gen_like_2,
            gen_like_schema_fail,
            gen_write_fail,
            gen_follow,
            gen_like_rejected,
        ):
            db.repos.insert_generation(generation, conn)
        for proposed in (
            proposed_like_valid_1,
            proposed_like_valid_2,
            proposed_like_rejected,
            proposed_follow_valid,
        ):
            db.repos.insert_proposed_action(proposed, conn)
        for like in (like_1, like_2):
            db.repos.insert_like(like, conn)
        db.repos.insert_follow(follow_1, conn)
        for feed in (feed_healthy, feed_empty, feed_duplicate, feed_self, feed_author):
            db.repos.insert_generated_feed(feed, conn)

    return EvalFixture(
        db_path=db_path,
        run_id=run.run_id,
        turn_id=turn.turn_id,
        turn_number=turn.turn_number,
    )
