"""Random-simple comment generation algorithm.

Selects top-k posts by recency + social proof, then uses random probability
and hardcoded text to decide whether to comment and which text to use.
"""

from __future__ import annotations

import random
from datetime import datetime, timezone

from lib.timestamp_utils import get_current_timestamp
from simulation.core.action_generators.interfaces import CommentGenerator
from simulation.core.models.actions import Comment
from simulation.core.models.generated.base import GenerationMetadata
from simulation.core.models.generated.comment import GeneratedComment
from simulation.core.models.posts import BlueskyFeedPost

TOP_K_POSTS_TO_COMMENT: int = 3
COMMENT_PROBABILITY: float = 0.30
HARDCODED_COMMENT_TEXTS: tuple[str, ...] = (
    "Nice!",
    "Interesting take.",
    "Totally agree.",
    "This resonates.",
    "Thanks for sharing.",
)
RECENCY_WEIGHT: float = 1.0
LIKE_COUNT_WEIGHT: float = 1.0
REPOST_WEIGHT: float = 0.5
REPLY_WEIGHT: float = 0.5
EXPLANATION: str = "Simple: random probability and hardcoded text"
CREATED_AT_FORMAT: str = "%Y_%m_%d-%H:%M:%S"


class RandomSimpleCommentGenerator(CommentGenerator):
    """Generates comments using scoring (recency + social proof) and random probability."""

    def generate(
        self,
        *,
        candidates: list[BlueskyFeedPost],
        run_id: str,
        turn_number: int,
        agent_handle: str,
    ) -> list[GeneratedComment]:
        """Generate comments from candidates using scoring and random probability."""
        if not candidates:
            return []

        scored = [(_score_post(post), post) for post in candidates]
        scored.sort(key=lambda x: (-x[0], x[1].id))
        selected = [post for _, post in scored[:TOP_K_POSTS_TO_COMMENT]]

        generated: list[GeneratedComment] = []
        for post in selected:
            if not _should_comment(
                run_id=run_id,
                turn_number=turn_number,
                agent_handle=agent_handle,
                post_id=post.id,
            ):
                continue
            generated.append(
                _build_generated_comment(
                    post=post,
                    agent_handle=agent_handle,
                    run_id=run_id,
                    turn_number=turn_number,
                )
            )

        # Treat ordering as part of the contract; keep it stable.
        generated.sort(key=lambda c: c.comment.post_id)
        return generated


def _score_post(post: BlueskyFeedPost) -> float:
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


def _should_comment(
    *,
    run_id: str,
    turn_number: int,
    agent_handle: str,
    post_id: str,
) -> bool:
    """Return whether to comment on a post using random probability in [0, 1)."""
    return random.random() < COMMENT_PROBABILITY


def _pick_comment_text(
    *,
    run_id: str,
    turn_number: int,
    agent_handle: str,
    post_id: str,
) -> str:
    """Pick a comment text from the hardcoded pool using random index."""
    roll = random.random()  # [0.0, 1.0)
    idx = int(roll * len(HARDCODED_COMMENT_TEXTS))
    return HARDCODED_COMMENT_TEXTS[idx]


def _build_generated_comment(
    *,
    post: BlueskyFeedPost,
    agent_handle: str,
    run_id: str,
    turn_number: int,
) -> GeneratedComment:
    """Build a GeneratedComment with IDs and metadata."""
    post_id = post.id
    comment_id = f"comment_{run_id}_{turn_number}_{agent_handle}_{post_id}"
    created_at = get_current_timestamp()
    text = _pick_comment_text(
        run_id=run_id,
        turn_number=turn_number,
        agent_handle=agent_handle,
        post_id=post_id,
    )
    return GeneratedComment(
        comment=Comment(
            comment_id=comment_id,
            agent_id=agent_handle,
            post_id=post_id,
            text=text,
            created_at=created_at,
        ),
        explanation=EXPLANATION,
        metadata=GenerationMetadata(
            model_used=None,
            generation_metadata={"policy": "simple"},
            created_at=created_at,
        ),
    )
