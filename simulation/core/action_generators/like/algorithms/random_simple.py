"""Random-simple like generation algorithm.

Selects top-k posts by recency + social proof, then uses random probability
to decide whether to like each.
"""

from __future__ import annotations

import random
from datetime import datetime, timezone

from lib.timestamp_utils import get_current_timestamp
from simulation.core.action_generators.interfaces import LikeGenerator
from simulation.core.models.actions import Like
from simulation.core.models.generated.base import GenerationMetadata
from simulation.core.models.generated.like import GeneratedLike
from simulation.core.models.posts import Post

TOP_K_POSTS_TO_LIKE: int = 2
LIKE_PROBABILITY: float = 0.30
RECENCY_WEIGHT: float = 1.0
LIKE_COUNT_WEIGHT: float = 1.0
REPOST_WEIGHT: float = 0.5
REPLY_WEIGHT: float = 0.5
EXPLANATION: str = "Simple: recency/social proof with random probability"
CREATED_AT_FORMAT: str = "%Y_%m_%d-%H:%M:%S"
LIKE_POLICY: str = "simple"


class RandomSimpleLikeGenerator(LikeGenerator):
    """Generates likes using scoring (recency + social proof) and random probability."""

    def generate(
        self,
        *,
        candidates: list[Post],
        run_id: str,
        turn_number: int,
        agent_handle: str,
    ) -> list[GeneratedLike]:
        """Generate likes from candidates using scoring and random probability."""
        if not candidates:
            return []

        scored = [(_score_post(post), post) for post in candidates]
        scored.sort(key=lambda x: (-x[0], x[1].post_id))
        selected = [post for _, post in scored[:TOP_K_POSTS_TO_LIKE]]

        generated: list[GeneratedLike] = []
        for post in selected:
            if not _should_like():
                continue
            generated.append(
                _build_generated_like(
                    post=post,
                    agent_handle=agent_handle,
                    run_id=run_id,
                    turn_number=turn_number,
                )
            )

        return generated


def _score_post(post: Post) -> float:
    """Compute score for a post (recency + social proof)."""
    recency = _recency_score(post.created_at)
    social = (
        post.like_count * LIKE_COUNT_WEIGHT
        + post.repost_count * REPOST_WEIGHT
        + post.reply_count * REPLY_WEIGHT
    )
    return recency * RECENCY_WEIGHT + social


def _recency_score(created_at: str) -> float:
    """Convert created_at to a numeric recency score (higher = newer)."""
    try:
        dt = datetime.strptime(created_at, CREATED_AT_FORMAT)
        dt = dt.replace(tzinfo=timezone.utc)
        return float(dt.timestamp())
    except (ValueError, TypeError):
        return 0.0


def _should_like() -> bool:
    """Return whether to like using random probability in [0, 1)."""
    return random.random() < LIKE_PROBABILITY


def _build_generated_like(
    *,
    post: Post,
    agent_handle: str,
    run_id: str,
    turn_number: int,
) -> GeneratedLike:
    """Build a GeneratedLike with IDs and metadata."""
    post_id = post.post_id
    like_id = f"like_{run_id}_{turn_number}_{agent_handle}_{post_id}"
    created_at = get_current_timestamp()
    return GeneratedLike(
        like=Like(
            like_id=like_id,
            agent_id=agent_handle,
            post_id=post_id,
            created_at=created_at,
        ),
        explanation=EXPLANATION,
        metadata=GenerationMetadata(
            model_used=None,
            generation_metadata={
                "policy": LIKE_POLICY,
                "like_probability": LIKE_PROBABILITY,
            },
            created_at=created_at,
        ),
    )
