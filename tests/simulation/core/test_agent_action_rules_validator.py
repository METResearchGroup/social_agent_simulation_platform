"""Tests for simulation.core.agent_action_rules_validator module."""

import pytest

from simulation.core.action_history import InMemoryActionHistoryStore
from simulation.core.agent_action_rules_validator import AgentActionRulesValidator
from tests.factories import (
    GeneratedCommentFactory,
    GeneratedFollowFactory,
    GeneratedLikeFactory,
    GenerationMetadataFactory,
)


def _meta():
    return GenerationMetadataFactory.create(created_at="2024_01_01-12:00:00")


@pytest.fixture
def policy():
    return AgentActionRulesValidator()


@pytest.fixture
def history():
    return InMemoryActionHistoryStore()


def test_raises_for_duplicate_like_within_same_turn(policy, history):
    with pytest.raises(ValueError, match="liked duplicate targets"):
        policy.validate(
            run_id="run_123",
            turn_number=0,
            agent_handle="agent1.bsky.social",
            likes=[
                GeneratedLikeFactory.create(
                    agent_id="agent1",
                    post_id="post_1",
                    explanation="reason",
                    metadata=_meta(),
                ),
                GeneratedLikeFactory.create(
                    agent_id="agent1",
                    post_id="post_1",
                    explanation="reason",
                    metadata=_meta(),
                ),
            ],
            comments=[],
            follows=[],
            action_history_store=history,
        )


def test_raises_for_duplicate_comment_within_same_turn(policy, history):
    with pytest.raises(ValueError, match="commented duplicate targets"):
        policy.validate(
            run_id="run_123",
            turn_number=0,
            agent_handle="agent1.bsky.social",
            likes=[],
            comments=[
                GeneratedCommentFactory.create(
                    agent_id="agent1",
                    post_id="post_1",
                    text="nice post",
                    explanation="reason",
                    metadata=_meta(),
                ),
                GeneratedCommentFactory.create(
                    agent_id="agent1",
                    post_id="post_1",
                    text="nice post",
                    explanation="reason",
                    metadata=_meta(),
                ),
            ],
            follows=[],
            action_history_store=history,
        )


def test_raises_for_duplicate_follow_within_same_turn(policy, history):
    with pytest.raises(ValueError, match="followed duplicate targets"):
        policy.validate(
            run_id="run_123",
            turn_number=0,
            agent_handle="agent1.bsky.social",
            likes=[],
            comments=[],
            follows=[
                GeneratedFollowFactory.create(
                    agent_id="agent1",
                    user_id="user_1",
                    explanation="reason",
                    metadata=_meta(),
                ),
                GeneratedFollowFactory.create(
                    agent_id="agent1",
                    user_id="user_1",
                    explanation="reason",
                    metadata=_meta(),
                ),
            ],
            action_history_store=history,
        )


def test_raises_for_previously_seen_targets_across_turns(policy, history):
    like_post_ids, comment_post_ids, follow_user_ids = policy.validate(
        run_id="run_123",
        turn_number=0,
        agent_handle="agent1.bsky.social",
        likes=[
            GeneratedLikeFactory.create(
                agent_id="agent1",
                post_id="post_1",
                explanation="reason",
                metadata=_meta(),
            )
        ],
        comments=[
            GeneratedCommentFactory.create(
                agent_id="agent1",
                post_id="post_2",
                text="nice post",
                explanation="reason",
                metadata=_meta(),
            )
        ],
        follows=[
            GeneratedFollowFactory.create(
                agent_id="agent1",
                user_id="user_3",
                explanation="reason",
                metadata=_meta(),
            )
        ],
        action_history_store=history,
    )
    history.record_like("run_123", "agent1.bsky.social", like_post_ids[0])
    history.record_comment("run_123", "agent1.bsky.social", comment_post_ids[0])
    history.record_follow("run_123", "agent1.bsky.social", follow_user_ids[0])

    with pytest.raises(ValueError, match="cannot like post post_1 again"):
        policy.validate(
            run_id="run_123",
            turn_number=1,
            agent_handle="agent1.bsky.social",
            likes=[
                GeneratedLikeFactory.create(
                    agent_id="agent1",
                    post_id="post_1",
                    explanation="reason",
                    metadata=_meta(),
                )
            ],
            comments=[],
            follows=[],
            action_history_store=history,
        )


def test_distinct_targets_pass_and_returns_identifiers(policy, history):
    likes = [
        GeneratedLikeFactory.create(
            agent_id="agent1", post_id="post_1", explanation="reason", metadata=_meta()
        )
    ]
    comments = [
        GeneratedCommentFactory.create(
            agent_id="agent1",
            post_id="post_2",
            text="nice post",
            explanation="reason",
            metadata=_meta(),
        )
    ]
    follows = [
        GeneratedFollowFactory.create(
            agent_id="agent1", user_id="user_3", explanation="reason", metadata=_meta()
        )
    ]

    like_post_ids, comment_post_ids, follow_user_ids = policy.validate(
        run_id="run_123",
        turn_number=0,
        agent_handle="agent1.bsky.social",
        likes=likes,
        comments=comments,
        follows=follows,
        action_history_store=history,
    )

    assert like_post_ids == ["post_1"]
    assert comment_post_ids == ["post_2"]
    assert follow_user_ids == ["user_3"]
    assert not history.has_liked("run_123", "agent1.bsky.social", "post_1")
