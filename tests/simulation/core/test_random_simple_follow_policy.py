"""Tests for simulation.core.action_generators.follow.algorithms.random_simple module."""

import re

import simulation.core.action_generators.follow.algorithms.random_simple as random_simple_follow
from simulation.core.action_generators.follow.algorithms.random_simple import (
    FOLLOW_POLICY,
    TOP_K_USERS_TO_FOLLOW,
    RandomSimpleFollowGenerator,
)
from simulation.core.models.posts import BlueskyFeedPost
from tests.factories import PostFactory

# Timestamp format used by get_current_timestamp(): YYYY_MM_DD-HH:MM:SS
CREATED_AT_PATTERN = re.compile(r"^\d{4}_\d{2}_\d{2}-\d{2}:\d{2}:\d{2}$")


def _post(
    post_id: str,
    *,
    author_handle: str | None = None,
    like_count: int = 0,
    repost_count: int = 0,
    reply_count: int = 0,
    created_at: str = "2024_01_01-12:00:00",
) -> BlueskyFeedPost:
    """Build a BlueskyFeedPost for tests."""
    resolved_author_handle: str = author_handle or f"author-{post_id}.bsky.social"
    return PostFactory.create(
        post_id=post_id,
        uri=post_id,
        author_handle=resolved_author_handle,
        author_display_name=f"Author {post_id}",
        text="content",
        like_count=like_count,
        bookmark_count=0,
        quote_count=0,
        reply_count=reply_count,
        repost_count=repost_count,
        created_at=created_at,
    )


def test_returns_empty_when_no_candidates():
    """Empty candidates returns empty list."""
    generator = RandomSimpleFollowGenerator()
    result = generator.generate(
        candidates=[],
        run_id="run_1",
        turn_number=0,
        agent_handle="agent1.bsky.social",
    )
    expected_result: list = []
    assert result == expected_result


def test_respects_top_k_limit_when_probability_allows(monkeypatch):
    """Never returns more than TOP_K follows."""
    monkeypatch.setattr(random_simple_follow, "FOLLOW_PROBABILITY", 1.0)
    generator = RandomSimpleFollowGenerator()
    candidates = [
        _post(f"post_{index}", author_handle=f"author-{index}.bsky.social")
        for index in range(5)
    ]
    result = generator.generate(
        candidates=candidates,
        run_id="run_1",
        turn_number=0,
        agent_handle="agent1.bsky.social",
    )
    expected_count = min(TOP_K_USERS_TO_FOLLOW, len(candidates))
    assert len(result) == expected_count


def test_deduplicates_author_candidates(monkeypatch):
    """Same author can only be followed once per generation."""
    monkeypatch.setattr(random_simple_follow, "FOLLOW_PROBABILITY", 1.0)
    generator = RandomSimpleFollowGenerator()
    candidates = [
        _post("post_a1", author_handle="author-a.bsky.social", like_count=5),
        _post("post_a2", author_handle="author-a.bsky.social", like_count=10),
        _post("post_b", author_handle="author-b.bsky.social", like_count=8),
    ]
    result = generator.generate(
        candidates=candidates,
        run_id="run_42",
        turn_number=3,
        agent_handle="agent1.bsky.social",
    )
    followed_user_ids = [follow.follow.user_id for follow in result]
    expected_unique_count = len(set(followed_user_ids))
    assert len(followed_user_ids) == expected_unique_count


def test_excludes_self_from_follow_candidates(monkeypatch):
    """Agent never follows itself even if self-authored posts appear in feed."""
    monkeypatch.setattr(random_simple_follow, "FOLLOW_PROBABILITY", 1.0)
    generator = RandomSimpleFollowGenerator()
    agent_handle = "agent.bsky.social"
    candidates = [
        _post("self_post", author_handle=agent_handle),
        _post("other_post", author_handle="other-user.bsky.social"),
    ]
    result = generator.generate(
        candidates=candidates,
        run_id="run_self",
        turn_number=0,
        agent_handle=agent_handle,
    )
    followed_user_ids = [follow.follow.user_id for follow in result]
    assert agent_handle not in followed_user_ids
    expected_other_user = "other-user.bsky.social"
    assert expected_other_user in followed_user_ids


def test_threshold_boundary_includes_below_and_excludes_equal(monkeypatch):
    """Random below threshold yields follow; at-or-above threshold does not."""
    monkeypatch.setattr(random_simple_follow, "FOLLOW_PROBABILITY", 0.30)
    roll_values = iter([0.29, 0.30])

    def _fake_random() -> float:
        return next(roll_values)

    monkeypatch.setattr(random_simple_follow.random, "random", _fake_random)
    generator = RandomSimpleFollowGenerator()
    candidates = [
        _post("post_a", author_handle="author-a.bsky.social"),
        _post("post_b", author_handle="author-b.bsky.social"),
    ]
    result = generator.generate(
        candidates=candidates,
        run_id="run_threshold",
        turn_number=5,
        agent_handle="agent1.bsky.social",
    )
    followed_user_ids = [follow.follow.user_id for follow in result]
    expected_result = ["author-a.bsky.social"]
    assert followed_user_ids == expected_result


def test_generated_follow_has_required_fields_and_metadata(monkeypatch):
    """GeneratedFollow contains IDs, real created_at, and metadata (policy simple, no roll)."""
    monkeypatch.setattr(random_simple_follow, "FOLLOW_PROBABILITY", 0.5)
    monkeypatch.setattr(random_simple_follow.random, "random", lambda: 0.1)
    generator = RandomSimpleFollowGenerator()
    candidates = [
        _post("post_1", author_handle="target-user.bsky.social", like_count=1)
    ]
    result = generator.generate(
        candidates=candidates,
        run_id="run_1",
        turn_number=2,
        agent_handle="agent.bsky.social",
    )
    assert len(result) == 1
    follow = result[0]
    expected_run_id = "run_1"
    expected_turn = 2
    expected_handle = "agent.bsky.social"
    expected_user_id = "target-user.bsky.social"
    assert (
        follow.follow.follow_id
        == f"follow_{expected_run_id}_{expected_turn}_{expected_handle}_{expected_user_id}"
    )
    assert follow.follow.agent_id == expected_handle
    assert follow.follow.user_id == expected_user_id
    assert follow.explanation
    assert CREATED_AT_PATTERN.match(follow.follow.created_at), (
        f"created_at should be YYYY_MM_DD-HH:MM:SS, got {follow.follow.created_at!r}"
    )
    assert CREATED_AT_PATTERN.match(follow.metadata.created_at), (
        f"metadata.created_at should be YYYY_MM_DD-HH:MM:SS, got {follow.metadata.created_at!r}"
    )
    expected_generation_metadata = {
        "policy": FOLLOW_POLICY,
        "follow_probability": 0.5,
    }
    assert follow.metadata.generation_metadata == expected_generation_metadata
