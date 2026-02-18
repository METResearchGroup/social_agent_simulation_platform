"""Tests for simulation.core.action_generators.comment.algorithms.deterministic module."""

from simulation.core.action_generators.comment.algorithms import deterministic as mod
from simulation.core.action_generators.comment.algorithms.deterministic import (
    TOP_K_POSTS_TO_COMMENT,
    DeterministicCommentGenerator,
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
    generator = DeterministicCommentGenerator()
    result = generator.generate(
        candidates=[],
        run_id="run_1",
        turn_number=0,
        agent_handle="agent1.bsky.social",
    )
    expected_result: list = []
    assert result == expected_result


def test_returns_empty_when_probability_is_zero(monkeypatch):
    """Probability gate at 0% yields no comments."""
    monkeypatch.setattr(mod, "COMMENT_PROBABILITY_PCT", 0)
    generator = DeterministicCommentGenerator()
    candidates = [_post("post_1", like_count=10), _post("post_2", like_count=5)]
    result = generator.generate(
        candidates=candidates,
        run_id="run_prob0",
        turn_number=0,
        agent_handle="agent1.bsky.social",
    )
    expected_result: list = []
    assert result == expected_result


def test_returns_comments_when_probability_is_100(monkeypatch):
    """Probability gate at 100% yields comments for selected candidates."""
    monkeypatch.setattr(mod, "COMMENT_PROBABILITY_PCT", 100)
    generator = DeterministicCommentGenerator()
    candidates = [_post("post_1", like_count=10), _post("post_2", like_count=5)]
    result = generator.generate(
        candidates=candidates,
        run_id="run_prob100",
        turn_number=0,
        agent_handle="agent1.bsky.social",
    )
    expected_count = min(TOP_K_POSTS_TO_COMMENT, len(candidates))
    assert len(result) == expected_count
    assert all(c.comment.post_id in ("post_1", "post_2") for c in result)
    assert all(c.comment.text for c in result)


def test_selection_prefers_higher_social_proof(monkeypatch):
    """Top-k selection prefers higher like_count when recency is equal."""
    monkeypatch.setattr(mod, "COMMENT_PROBABILITY_PCT", 100)
    generator = DeterministicCommentGenerator()
    candidates = [
        _post("post_0", like_count=0),
        _post("post_1", like_count=1),
        _post("post_2", like_count=2),
        _post("post_3", like_count=3),
        _post("post_4", like_count=4),
    ]
    result = generator.generate(
        candidates=candidates,
        run_id="run_social",
        turn_number=0,
        agent_handle="agent1.bsky.social",
    )

    selected_post_ids = {c.comment.post_id for c in result}
    expected_selected = {f"post_{i}" for i in range(5 - TOP_K_POSTS_TO_COMMENT, 5)}
    assert selected_post_ids == expected_selected


def test_determinism_same_inputs_same_output(monkeypatch):
    """Repeated runs with identical inputs produce same comments."""
    monkeypatch.setattr(mod, "COMMENT_PROBABILITY_PCT", 100)
    generator = DeterministicCommentGenerator()
    candidates = [_post("post_a", like_count=3), _post("post_b", like_count=7)]
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

    expected_post_ids = [c.comment.post_id for c in result1]
    expected_texts = [c.comment.text for c in result1]
    assert [c.comment.post_id for c in result2] == expected_post_ids
    assert [c.comment.text for c in result2] == expected_texts


def test_ordering_is_sorted_by_post_id(monkeypatch):
    """Output ordering is stable and sorted by post_id."""
    monkeypatch.setattr(mod, "COMMENT_PROBABILITY_PCT", 100)
    generator = DeterministicCommentGenerator()
    candidates = [_post("b"), _post("a")]

    result = generator.generate(
        candidates=candidates,
        run_id="run_order",
        turn_number=0,
        agent_handle="agent1.bsky.social",
    )

    expected_order = ["a", "b"]
    assert [c.comment.post_id for c in result] == expected_order


def test_generated_comment_has_required_fields(monkeypatch):
    """GeneratedComment has valid comment_id, agent_id, post_id, text, explanation, metadata."""
    monkeypatch.setattr(mod, "COMMENT_PROBABILITY_PCT", 100)
    generator = DeterministicCommentGenerator()
    candidates = [_post("post_1", like_count=1)]
    result = generator.generate(
        candidates=candidates,
        run_id="run_1",
        turn_number=2,
        agent_handle="agent.bsky.social",
    )
    assert len(result) == 1
    comment = result[0]
    expected_run_id = "run_1"
    expected_turn = 2
    expected_handle = "agent.bsky.social"
    expected_post_id = "post_1"
    assert (
        comment.comment.comment_id
        == f"comment_{expected_run_id}_{expected_turn}_{expected_handle}_{expected_post_id}"
    )
    assert comment.comment.agent_id == expected_handle
    assert comment.comment.post_id == expected_post_id
    assert comment.comment.text
    assert comment.explanation
    assert comment.metadata.generation_metadata == {"policy": "deterministic"}
