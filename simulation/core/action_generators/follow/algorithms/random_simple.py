"""Random-simple follow generation algorithm.

Selects top-k authors by recency + social proof, then uses random probability
to decide whether to follow each.
"""

from __future__ import annotations

import random
from datetime import datetime, timezone

from lib.timestamp_utils import CREATED_AT_FORMAT, get_current_timestamp
from simulation.core.action_generators.interfaces import FollowGenerator
from simulation.core.models.actions import Follow
from simulation.core.models.generated.base import GenerationMetadata
from simulation.core.models.generated.follow import GeneratedFollow
from simulation.core.models.posts import Post

TOP_K_USERS_TO_FOLLOW: int = 2
FOLLOW_PROBABILITY: float = 0.30
RECENCY_WEIGHT: float = 1.0
LIKE_COUNT_WEIGHT: float = 1.0
REPOST_WEIGHT: float = 0.5
REPLY_WEIGHT: float = 0.5
EXPLANATION: str = "Simple: recency/social proof with random probability"
FOLLOW_POLICY: str = "simple"


class RandomSimpleFollowGenerator(FollowGenerator):
    """Generates follows using scoring (recency + social proof) and random probability."""

    def generate(
        self,
        *,
        candidates: list[Post],
        run_id: str,
        turn_number: int,
        agent_handle: str,
        agent_id: str,
    ) -> list[GeneratedFollow]:
        """Generate follows from candidates using scoring and random probability."""
        if not candidates:
            return []

        scored_candidates: list[tuple[float, Post]] = _collect_scored_unique_authors(
            candidates=candidates,
            agent_id=agent_id,
        )
        if not scored_candidates:
            return []

        generated_follows: list[GeneratedFollow] = []
        for _, post in scored_candidates:
            if not _should_follow():
                continue

            generated_follow: GeneratedFollow = _build_generated_follow(
                post=post,
                agent_handle=agent_handle,
                agent_id=agent_id,
                run_id=run_id,
                turn_number=turn_number,
            )
            generated_follows.append(generated_follow)
            if len(generated_follows) >= TOP_K_USERS_TO_FOLLOW:
                break

        return generated_follows


def _collect_scored_unique_authors(
    *,
    candidates: list[Post],
    agent_id: str,
) -> list[tuple[float, Post]]:
    """Choose one best post per author ``agent_id`` and return sorted tuples by score."""
    best_by_author: dict[str, tuple[float, Post]] = {}
    for post in candidates:
        author_agent_id_key = post.author_agent_id
        if author_agent_id_key == agent_id:
            continue

        score: float = _score_post(post)
        existing: tuple[float, Post] | None = best_by_author.get(author_agent_id_key)
        if existing is None:
            best_by_author[author_agent_id_key] = (score, post)
            continue

        existing_score, existing_post = existing
        if score > existing_score or (
            score == existing_score and post.post_id < existing_post.post_id
        ):
            best_by_author[author_agent_id_key] = (score, post)

    scored: list[tuple[float, Post]] = list(best_by_author.values())
    scored.sort(
        key=lambda scored_post: (
            -scored_post[0],
            scored_post[1].author_handle,
            scored_post[1].post_id,
        )
    )
    return scored


def _score_post(post: Post) -> float:
    """Compute score for selecting follow candidates (recency + social proof)."""
    recency_score: float = _recency_score(created_at=post.created_at)
    social_score: float = (
        post.like_count * LIKE_COUNT_WEIGHT
        + post.repost_count * REPOST_WEIGHT
        + post.reply_count * REPLY_WEIGHT
    )
    return recency_score * RECENCY_WEIGHT + social_score


def _recency_score(*, created_at: str) -> float:
    """Convert created_at to a numeric recency score (higher = newer)."""
    try:
        created_at_dt = datetime.strptime(created_at, CREATED_AT_FORMAT)
        created_at_dt = created_at_dt.replace(tzinfo=timezone.utc)
        return float(created_at_dt.timestamp())
    except (TypeError, ValueError):
        return 0.0


def _should_follow() -> bool:
    """Return whether to follow using random probability in [0, 1)."""
    return random.random() < FOLLOW_PROBABILITY  # nosec B311


def _build_generated_follow(
    *,
    post: Post,
    agent_handle: str,
    agent_id: str,
    run_id: str,
    turn_number: int,
) -> GeneratedFollow:
    """Build a GeneratedFollow with IDs and metadata."""
    target_agent_id: str = post.author_agent_id
    follow_id: str = f"follow_{run_id}_{turn_number}_{agent_handle}_{target_agent_id}"
    created_at: str = get_current_timestamp()
    generation_metadata: dict[str, float | str] = {
        "policy": FOLLOW_POLICY,
        "follow_probability": FOLLOW_PROBABILITY,
    }
    return GeneratedFollow(
        follow=Follow(
            follow_id=follow_id,
            agent_id=agent_id,
            target_agent_id=target_agent_id,
            created_at=created_at,
        ),
        explanation=EXPLANATION,
        metadata=GenerationMetadata(
            model_used=None,
            generation_metadata=generation_metadata,
            created_at=created_at,
        ),
    )
