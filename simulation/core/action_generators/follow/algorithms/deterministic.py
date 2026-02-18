"""Deterministic follow generation algorithm.

Produces reproducible follows based on recency/social-proof scoring and a
deterministic probability gate.
"""

import hashlib
from datetime import datetime, timezone

from simulation.core.action_generators.interfaces import FollowGenerator
from simulation.core.models.actions import Follow
from simulation.core.models.generated.base import GenerationMetadata
from simulation.core.models.generated.follow import GeneratedFollow
from simulation.core.models.posts import BlueskyFeedPost

TOP_K_USERS_TO_FOLLOW: int = 2
FOLLOW_PROBABILITY: float = 0.30
RECENCY_WEIGHT: float = 1.0
LIKE_COUNT_WEIGHT: float = 1.0
REPOST_WEIGHT: float = 0.5
REPLY_WEIGHT: float = 0.5
EXPLANATION: str = "Deterministic: recency/social proof with probability gate"
CREATED_AT_FORMAT: str = "%Y_%m_%d-%H:%M:%S"
ROLL_HASH_PREFIX_HEX_LENGTH: int = 8
ROLL_HASH_DENOMINATOR: float = float(16**ROLL_HASH_PREFIX_HEX_LENGTH)
FOLLOW_POLICY: str = "deterministic"


class DeterministicFollowGenerator(FollowGenerator):
    """Generates follows using deterministic scoring and probability gating."""

    def generate(
        self,
        *,
        candidates: list[BlueskyFeedPost],
        run_id: str,
        turn_number: int,
        agent_handle: str,
    ) -> list[GeneratedFollow]:
        """Generate follows from candidates using deterministic scoring."""
        if not candidates:
            return []

        scored_candidates: list[tuple[float, BlueskyFeedPost]] = (
            _collect_scored_unique_authors(
                candidates=candidates,
                agent_handle=agent_handle,
            )
        )
        if not scored_candidates:
            return []

        generated_follows: list[GeneratedFollow] = []
        for _, post in scored_candidates:
            follow_roll: float = _deterministic_roll(
                run_id=run_id,
                turn_number=turn_number,
                agent_handle=agent_handle,
                user_id=post.author_handle,
            )
            if follow_roll >= FOLLOW_PROBABILITY:
                continue

            generated_follow: GeneratedFollow = _build_generated_follow(
                post=post,
                agent_handle=agent_handle,
                run_id=run_id,
                turn_number=turn_number,
                user_index=len(generated_follows),
                follow_roll=follow_roll,
            )
            generated_follows.append(generated_follow)
            if len(generated_follows) >= TOP_K_USERS_TO_FOLLOW:
                break

        return generated_follows


def _collect_scored_unique_authors(
    *,
    candidates: list[BlueskyFeedPost],
    agent_handle: str,
) -> list[tuple[float, BlueskyFeedPost]]:
    """Choose one best post per author and return deterministically sorted tuples."""
    best_by_author: dict[str, tuple[float, BlueskyFeedPost]] = {}
    for post in candidates:
        author_handle = post.author_handle
        if author_handle == agent_handle:
            continue

        score: float = _score_post(post)
        existing: tuple[float, BlueskyFeedPost] | None = best_by_author.get(
            author_handle
        )
        if existing is None:
            best_by_author[author_handle] = (score, post)
            continue

        existing_score, existing_post = existing
        if score > existing_score or (
            score == existing_score and post.id < existing_post.id
        ):
            best_by_author[author_handle] = (score, post)

    scored: list[tuple[float, BlueskyFeedPost]] = list(best_by_author.values())
    scored.sort(
        key=lambda scored_post: (
            -scored_post[0],
            scored_post[1].author_handle,
            scored_post[1].id,
        )
    )
    return scored


def _score_post(post: BlueskyFeedPost) -> float:
    """Compute deterministic score for selecting follow candidates."""
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


def _deterministic_roll(
    *,
    run_id: str,
    turn_number: int,
    agent_handle: str,
    user_id: str,
) -> float:
    """Generate deterministic pseudo-random roll in [0, 1)."""
    seed = f"{run_id}:{turn_number}:{agent_handle}:{user_id}"
    digest: str = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    prefix: str = digest[:ROLL_HASH_PREFIX_HEX_LENGTH]
    return int(prefix, 16) / ROLL_HASH_DENOMINATOR


def _derive_created_at(
    *,
    run_id: str,
    turn_number: int,
    agent_handle: str,
    user_index: int,
) -> str:
    """Derive deterministic created_at string for GeneratedFollow metadata."""
    return f"det_{run_id}_turn{turn_number}_{agent_handle}_{user_index}"


def _build_generated_follow(
    *,
    post: BlueskyFeedPost,
    agent_handle: str,
    run_id: str,
    turn_number: int,
    user_index: int,
    follow_roll: float,
) -> GeneratedFollow:
    """Build a GeneratedFollow with deterministic IDs and metadata."""
    user_id: str = post.author_handle
    follow_id: str = f"follow_{run_id}_{turn_number}_{agent_handle}_{user_id}"
    created_at: str = _derive_created_at(
        run_id=run_id,
        turn_number=turn_number,
        agent_handle=agent_handle,
        user_index=user_index,
    )
    generation_metadata: dict[str, float | str] = {
        "policy": FOLLOW_POLICY,
        "follow_probability": FOLLOW_PROBABILITY,
        "roll": follow_roll,
    }
    return GeneratedFollow(
        follow=Follow(
            follow_id=follow_id,
            agent_id=agent_handle,
            user_id=user_id,
            created_at=created_at,
        ),
        explanation=EXPLANATION,
        metadata=GenerationMetadata(
            model_used=None,
            generation_metadata=generation_metadata,
            created_at=created_at,
        ),
    )
