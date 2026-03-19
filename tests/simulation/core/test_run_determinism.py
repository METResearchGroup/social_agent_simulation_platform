"""Regression tests for simulation run determinism (seeded RNG).

Verifies that a fixed run_seed produces identical action sequences across
repeated runs, and that different seeds can produce different outputs.
"""

from __future__ import annotations

from simulation.core.agent_actions import (
    generate_comments,
    generate_follows,
    generate_likes,
)
from simulation.core.models.posts import Post
from tests.factories import PostFactory


def _post(
    uri: str,
    *,
    author_handle: str | None = None,
    like_count: int = 5,
    created_at: str = "2024_01_01-12:00:00",
) -> Post:
    """Build a Post for determinism tests."""
    handle = author_handle or f"author-{uri}.bsky.social"
    return PostFactory.create(
        uri=uri,
        author_handle=handle,
        author_display_name=f"Author {uri}",
        text="content",
        like_count=like_count,
        bookmark_count=0,
        quote_count=0,
        reply_count=0,
        repost_count=0,
        created_at=created_at,
    )


class TestRunDeterminism:
    """Regression tests for reproducible simulation runs via run_seed."""

    def test_same_seed_produces_identical_likes(self) -> None:
        """Two calls with same run_seed and candidates yield identical like sequences."""
        candidates = [
            _post("post_1", like_count=10),
            _post("post_2", like_count=5),
            _post("post_3", like_count=3),
        ]
        run_id = "run_det"
        run_seed = 99999
        turn_number = 0
        agent_handle = "agent.bsky.social"

        likes1 = generate_likes(
            candidates,
            run_id=run_id,
            run_seed=run_seed,
            turn_number=turn_number,
            agent_handle=agent_handle,
        )
        likes2 = generate_likes(
            candidates,
            run_id=run_id,
            run_seed=run_seed,
            turn_number=turn_number,
            agent_handle=agent_handle,
        )

        like_ids1 = sorted(g.like.like_id for g in likes1)
        like_ids2 = sorted(g.like.like_id for g in likes2)
        assert like_ids1 == like_ids2
        assert len(likes1) == len(likes2)

    def test_same_seed_produces_identical_comments(self) -> None:
        """Two calls with same run_seed and candidates yield identical comment sequences."""
        candidates = [
            _post("post_a", like_count=7),
            _post("post_b", like_count=4),
        ]
        run_id = "run_det"
        run_seed = 88888
        turn_number = 1
        agent_handle = "agent.bsky.social"

        comments1 = generate_comments(
            candidates,
            run_id=run_id,
            run_seed=run_seed,
            turn_number=turn_number,
            agent_handle=agent_handle,
        )
        comments2 = generate_comments(
            candidates,
            run_id=run_id,
            run_seed=run_seed,
            turn_number=turn_number,
            agent_handle=agent_handle,
        )

        comment_ids1 = sorted(c.comment.comment_id for c in comments1)
        comment_ids2 = sorted(c.comment.comment_id for c in comments2)
        assert comment_ids1 == comment_ids2
        texts1 = sorted((c.comment.post_id, c.comment.text) for c in comments1)
        texts2 = sorted((c.comment.post_id, c.comment.text) for c in comments2)
        assert texts1 == texts2

    def test_same_seed_produces_identical_follows(self) -> None:
        """Two calls with same run_seed and candidates yield identical follow sequences."""
        candidates = [
            _post("post_x", author_handle="alice.bsky.social"),
            _post("post_y", author_handle="bob.bsky.social"),
        ]
        run_id = "run_det"
        run_seed = 77777
        turn_number = 2
        agent_handle = "observer.bsky.social"

        follows1 = generate_follows(
            candidates,
            run_id=run_id,
            run_seed=run_seed,
            turn_number=turn_number,
            agent_handle=agent_handle,
        )
        follows2 = generate_follows(
            candidates,
            run_id=run_id,
            run_seed=run_seed,
            turn_number=turn_number,
            agent_handle=agent_handle,
        )

        follow_ids1 = sorted(f.follow.follow_id for f in follows1)
        follow_ids2 = sorted(f.follow.follow_id for f in follows2)
        assert follow_ids1 == follow_ids2

    def test_different_seeds_can_produce_different_outputs(self) -> None:
        """Different run_seed values can produce different action sequences."""
        candidates = [
            _post("post_1", like_count=10),
            _post("post_2", like_count=8),
            _post("post_3", like_count=6),
        ]
        run_id = "run_diff"
        turn_number = 0
        agent_handle = "agent.bsky.social"

        # Try multiple seed pairs; with 0.3 probability, different seeds often differ
        seed_a = 11111
        seed_b = 22222

        likes_a = generate_likes(
            candidates,
            run_id=run_id,
            run_seed=seed_a,
            turn_number=turn_number,
            agent_handle=agent_handle,
        )
        likes_b = generate_likes(
            candidates,
            run_id=run_id,
            run_seed=seed_b,
            turn_number=turn_number,
            agent_handle=agent_handle,
        )

        like_ids_a = sorted(g.like.like_id for g in likes_a)
        like_ids_b = sorted(g.like.like_id for g in likes_b)
        # Different seeds should produce different outputs (probabilistically very likely)
        assert like_ids_a != like_ids_b or len(likes_a) != len(likes_b)
