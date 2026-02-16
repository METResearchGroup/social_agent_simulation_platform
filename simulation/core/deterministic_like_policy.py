"""Deterministic like generation policy for agent actions.

Produces reproducible, non-zero likes based on recency and social proof
scoring. Domain-pure: imports only from simulation.core.models and stdlib.
"""

from datetime import datetime

from simulation.core.models.actions import Like
from simulation.core.models.generated.base import GenerationMetadata
from simulation.core.models.generated.like import GeneratedLike
from simulation.core.models.posts import BlueskyFeedPost

TOP_K_POSTS_TO_LIKE: int = 2
RECENCY_WEIGHT: float = 1.0
LIKE_COUNT_WEIGHT: float = 1.0
REPOST_WEIGHT: float = 0.5
REPLY_WEIGHT: float = 0.5
AI_REASON: str = "Deterministic: recency and social proof"
CREATED_AT_FORMAT: str = "%Y_%m_%d-%H:%M:%S"


def generate_deterministic_likes(
    *,
    candidates: list[BlueskyFeedPost],
    run_id: str,
    turn_number: int,
    agent_handle: str,
) -> list[GeneratedLike]:
    """Generate likes from candidates using deterministic scoring.

    Scores each candidate by recency and social proof (like_count,
    repost_count, reply_count), selects the top k, and builds
    GeneratedLike objects with deterministic IDs and metadata.

    Args:
        candidates: Like-eligible feed posts (already filtered for
            history and own-posts exclusion by callers).
        run_id: Run identifier for deterministic IDs.
        turn_number: Turn number for deterministic IDs.
        agent_handle: Agent handle for deterministic IDs and Like.agent_id.

    Returns:
        Up to TOP_K_POSTS_TO_LIKE GeneratedLike instances, ordered by
        score descending then by post.id for deterministic output.
    """
    if not candidates:
        return []

    scored = [(_score_post(post, agent_handle), post) for post in candidates]
    scored.sort(key=lambda x: (-x[0], x[1].id))
    selected = scored[:TOP_K_POSTS_TO_LIKE]

    return [
        _build_generated_like(
            post=post,
            agent_handle=agent_handle,
            run_id=run_id,
            turn_number=turn_number,
            post_index=idx,
        )
        for idx, (_, post) in enumerate(selected)
    ]


def _score_post(post: BlueskyFeedPost, agent_handle: str) -> float:
    """Compute deterministic score for a post.

    Combines recency (parsed from created_at) and social proof
    (like_count, repost_count, reply_count). Higher score = more
    likely to be liked.
    """
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
        return float(dt.timestamp())
    except (ValueError, TypeError):
        return 0.0


def _derive_created_at(
    run_id: str,
    turn_number: int,
    agent_handle: str,
    post_index: int,
) -> str:
    """Derive a deterministic created_at string for GeneratedLike metadata."""
    return f"det_{run_id}_turn{turn_number}_{agent_handle}_{post_index}"


def _build_generated_like(
    *,
    post: BlueskyFeedPost,
    agent_handle: str,
    run_id: str,
    turn_number: int,
    post_index: int,
) -> GeneratedLike:
    """Build a GeneratedLike with deterministic IDs and metadata."""
    post_id = post.id
    like_id = f"like_{run_id}_{turn_number}_{agent_handle}_{post_id}"
    created_at = _derive_created_at(
        run_id=run_id,
        turn_number=turn_number,
        agent_handle=agent_handle,
        post_index=post_index,
    )
    return GeneratedLike(
        like=Like(
            like_id=like_id,
            agent_id=agent_handle,
            post_id=post_id,
            created_at=created_at,
        ),
        ai_reason=AI_REASON,
        metadata=GenerationMetadata(
            model_used=None,
            generation_metadata={"policy": "deterministic"},
            created_at=created_at,
        ),
    )
