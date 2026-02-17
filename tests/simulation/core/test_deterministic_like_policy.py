"""Tests for simulation.core.action_generators.like.algorithms.deterministic module."""

from simulation.core.action_generators.like.algorithms.deterministic import (
    TOP_K_POSTS_TO_LIKE,
    DeterministicLikeGenerator,
)
from simulation.core.models.posts import BlueskyFeedPost


def _post(
    post_id: str,
    *,
    like_count: int = 0,
    repost_count: int = 0,
    reply_count: int = 0,
    created_at: str = "2024_01_01-12:00:00",
) -> BlueskyFeedPost:
    """Build a BlueskyFeedPost for tests."""
    return BlueskyFeedPost(
        id=post_id,
        uri=post_id,
        author_handle=f"author-{post_id}.bsky.social",
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
    generator = DeterministicLikeGenerator()
    result = generator.generate(
        candidates=[],
        run_id="run_1",
        turn_number=0,
        agent_handle="agent1.bsky.social",
    )
    expected_result: list = []
    assert result == expected_result


def test_returns_non_zero_likes_with_candidates():
    """Non-empty candidates with social proof produces likes."""
    generator = DeterministicLikeGenerator()
    candidates = [
        _post("post_1", like_count=10),
        _post("post_2", like_count=5),
    ]
    result = generator.generate(
        candidates=candidates,
        run_id="run_1",
        turn_number=0,
        agent_handle="agent1.bsky.social",
    )
    expected_count = min(TOP_K_POSTS_TO_LIKE, len(candidates))
    assert len(result) == expected_count
    assert len(result) > 0
    assert all(like.like.post_id in ("post_1", "post_2") for like in result)


def test_determinism_same_inputs_same_output():
    """Repeated runs with identical inputs produce same likes."""
    generator = DeterministicLikeGenerator()
    candidates = [
        _post("post_a", like_count=3),
        _post("post_b", like_count=7),
    ]
    run_id = "run_det"
    turn_number = 1
    agent_handle = "agent2.bsky.social"

    result1 = generator.generate(
        candidates=candidates,
        run_id=run_id,
        turn_number=turn_number,
        agent_handle=agent_handle,
    )
    result2 = generator.generate(
        candidates=candidates,
        run_id=run_id,
        turn_number=turn_number,
        agent_handle=agent_handle,
    )

    expected_post_ids = [like.like.post_id for like in result1]
    assert [like.like.post_id for like in result2] == expected_post_ids
    assert len(result1) == len(result2)


def test_respects_top_k_limit():
    """Never returns more than TOP_K likes."""
    generator = DeterministicLikeGenerator()
    candidates = [_post(f"post_{i}", like_count=i) for i in range(5)]
    result = generator.generate(
        candidates=candidates,
        run_id="run_1",
        turn_number=0,
        agent_handle="agent1.bsky.social",
    )
    expected_max = TOP_K_POSTS_TO_LIKE
    assert len(result) <= expected_max


def test_higher_social_proof_preferred():
    """Post with higher like_count is preferred (first) when selecting top-k."""
    generator = DeterministicLikeGenerator()
    low_social = _post("post_low", like_count=1)
    high_social = _post("post_high", like_count=100)
    candidates = [low_social, high_social]

    result = generator.generate(
        candidates=candidates,
        run_id="run_1",
        turn_number=0,
        agent_handle="agent1.bsky.social",
    )

    post_ids = [like.like.post_id for like in result]
    expected_first = "post_high"
    assert post_ids[0] == expected_first
    assert "post_high" in post_ids


def test_recency_affects_ordering():
    """Newer posts score higher (first) when social proof is equal."""
    generator = DeterministicLikeGenerator()
    old_post = _post("post_old", created_at="2024_01_01-00:00:00")
    new_post = _post("post_new", created_at="2024_12_31-23:59:59")
    candidates = [old_post, new_post]

    result = generator.generate(
        candidates=candidates,
        run_id="run_1",
        turn_number=0,
        agent_handle="agent1.bsky.social",
    )

    post_ids = [like.like.post_id for like in result]
    expected_first = "post_new"
    assert post_ids[0] == expected_first
    assert "post_new" in post_ids


def test_generated_like_has_required_fields():
    """GeneratedLike has valid like_id, agent_id, post_id, explanation, metadata."""
    generator = DeterministicLikeGenerator()
    candidates = [_post("post_1", like_count=1)]
    result = generator.generate(
        candidates=candidates,
        run_id="run_1",
        turn_number=2,
        agent_handle="agent.bsky.social",
    )
    assert len(result) == 1
    like = result[0]
    expected_run_id = "run_1"
    expected_turn = 2
    expected_handle = "agent.bsky.social"
    expected_post_id = "post_1"
    assert (
        like.like.like_id
        == f"like_{expected_run_id}_{expected_turn}_{expected_handle}_{expected_post_id}"
    )
    assert like.like.agent_id == expected_handle
    assert like.like.post_id == expected_post_id
    assert like.explanation
    assert like.metadata.generation_metadata == {"policy": "deterministic"}
