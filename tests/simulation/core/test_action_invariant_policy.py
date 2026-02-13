"""Tests for simulation.core.action_invariant_policy module."""

import pytest

from simulation.core.action_history import InMemoryActionHistoryStore
from simulation.core.action_invariant_policy import ActionInvariantPolicy
from simulation.core.models.actions import Comment, Follow, Like
from simulation.core.models.generated.base import GenerationMetadata
from simulation.core.models.generated.comment import GeneratedComment
from simulation.core.models.generated.follow import GeneratedFollow
from simulation.core.models.generated.like import GeneratedLike


def _meta() -> GenerationMetadata:
    return GenerationMetadata(created_at="2024_01_01-12:00:00")


def _like(agent_id: str, post_id: str) -> GeneratedLike:
    return GeneratedLike(
        like=Like(
            like_id=f"like_{agent_id}_{post_id}",
            agent_id=agent_id,
            post_id=post_id,
            created_at="2024_01_01-12:00:00",
        ),
        ai_reason="reason",
        metadata=_meta(),
    )


def _comment(agent_id: str, post_id: str) -> GeneratedComment:
    return GeneratedComment(
        comment=Comment(
            comment_id=f"comment_{agent_id}_{post_id}",
            agent_id=agent_id,
            post_id=post_id,
            created_at="2024_01_01-12:00:00",
        ),
        ai_reason="reason",
        metadata=_meta(),
    )


def _follow(agent_id: str, user_id: str) -> GeneratedFollow:
    return GeneratedFollow(
        follow=Follow(
            follow_id=f"follow_{agent_id}_{user_id}",
            agent_id=agent_id,
            user_id=user_id,
            created_at="2024_01_01-12:00:00",
        ),
        ai_reason="reason",
        metadata=_meta(),
    )


@pytest.fixture
def policy():
    return ActionInvariantPolicy()


@pytest.fixture
def history():
    return InMemoryActionHistoryStore()


def test_raises_for_duplicate_like_within_same_turn(policy, history):
    with pytest.raises(ValueError, match="liked duplicate targets"):
        policy.enforce(
            run_id="run_123",
            turn_number=0,
            agent_handle="agent1.bsky.social",
            likes=[_like("agent1", "post_1"), _like("agent1", "post_1")],
            comments=[],
            follows=[],
            action_history_store=history,
        )


def test_raises_for_duplicate_comment_within_same_turn(policy, history):
    with pytest.raises(ValueError, match="commented duplicate targets"):
        policy.enforce(
            run_id="run_123",
            turn_number=0,
            agent_handle="agent1.bsky.social",
            likes=[],
            comments=[_comment("agent1", "post_1"), _comment("agent1", "post_1")],
            follows=[],
            action_history_store=history,
        )


def test_raises_for_duplicate_follow_within_same_turn(policy, history):
    with pytest.raises(ValueError, match="followed duplicate targets"):
        policy.enforce(
            run_id="run_123",
            turn_number=0,
            agent_handle="agent1.bsky.social",
            likes=[],
            comments=[],
            follows=[_follow("agent1", "user_1"), _follow("agent1", "user_1")],
            action_history_store=history,
        )


def test_raises_for_previously_seen_targets_across_turns(policy, history):
    policy.enforce(
        run_id="run_123",
        turn_number=0,
        agent_handle="agent1.bsky.social",
        likes=[_like("agent1", "post_1")],
        comments=[_comment("agent1", "post_2")],
        follows=[_follow("agent1", "user_3")],
        action_history_store=history,
    )

    with pytest.raises(ValueError, match="cannot like post post_1 again"):
        policy.enforce(
            run_id="run_123",
            turn_number=1,
            agent_handle="agent1.bsky.social",
            likes=[_like("agent1", "post_1")],
            comments=[],
            follows=[],
            action_history_store=history,
        )


def test_distinct_targets_pass_and_record(policy, history):
    likes = [_like("agent1", "post_1")]
    comments = [_comment("agent1", "post_2")]
    follows = [_follow("agent1", "user_3")]

    accepted_likes, accepted_comments, accepted_follows = policy.enforce(
        run_id="run_123",
        turn_number=0,
        agent_handle="agent1.bsky.social",
        likes=likes,
        comments=comments,
        follows=follows,
        action_history_store=history,
    )

    assert accepted_likes == likes
    assert accepted_comments == comments
    assert accepted_follows == follows
    assert history.has_liked("run_123", "agent1.bsky.social", "post_1")
    assert history.has_commented("run_123", "agent1.bsky.social", "post_2")
    assert history.has_followed("run_123", "agent1.bsky.social", "user_3")
