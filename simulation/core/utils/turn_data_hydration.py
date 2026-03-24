from __future__ import annotations

import json

from simulation.core.models.actions import Comment, Follow, Like
from simulation.core.models.generated.base import GenerationMetadata
from simulation.core.models.generated.comment import GeneratedComment
from simulation.core.models.generated.follow import GeneratedFollow
from simulation.core.models.generated.like import GeneratedLike
from simulation.core.models.generated.post import GeneratedPost
from simulation.core.models.persisted_actions import (
    PersistedComment,
    PersistedFollow,
    PersistedLike,
)
from simulation.core.models.turn_posts import TurnPostSnapshot
from simulation.core.utils.interfaces import HasGenerationMetadataFields

DEFAULT_ACTION_EXPLANATION: str = "No explanation provided."


def _build_generation_metadata(row: HasGenerationMetadataFields) -> GenerationMetadata:
    meta_dict = (
        json.loads(row.generation_metadata_json)
        if row.generation_metadata_json
        else None
    )
    return GenerationMetadata(
        model_used=row.model_used,
        generation_metadata=meta_dict,
        created_at=row.generation_created_at or row.created_at,
    )


def normalize_action_explanation(explanation: str | None) -> str:
    """Normalize a persisted explanation into a non-empty string.

    Persisted rows may have NULL (or whitespace-only) explanation values; generated
    action models require a non-empty explanation.
    """
    normalized = (explanation or "").strip()
    return normalized or DEFAULT_ACTION_EXPLANATION


PersistedActionRow = PersistedLike | PersistedComment | PersistedFollow


def build_metadata(row: PersistedActionRow) -> GenerationMetadata:
    """Build GenerationMetadata from a persisted action row."""
    return _build_generation_metadata(row)


def persisted_like_to_generated(row: PersistedLike) -> GeneratedLike:
    """Build GeneratedLike from a PersistedLike row."""
    return GeneratedLike(
        like=Like(
            like_id=row.like_id,
            agent_id=row.agent_id,
            post_id=row.post_id,
            created_at=row.created_at,
        ),
        explanation=normalize_action_explanation(row.explanation),
        metadata=build_metadata(row),
    )


def persisted_comment_to_generated(row: PersistedComment) -> GeneratedComment:
    """Build GeneratedComment from a PersistedComment row."""
    return GeneratedComment(
        comment=Comment(
            comment_id=row.comment_id,
            agent_id=row.agent_id,
            post_id=row.post_id,
            text=row.text,
            created_at=row.created_at,
        ),
        explanation=normalize_action_explanation(row.explanation),
        metadata=build_metadata(row),
    )


def persisted_follow_to_generated(row: PersistedFollow) -> GeneratedFollow:
    """Build GeneratedFollow from a PersistedFollow row."""
    return GeneratedFollow(
        follow=Follow(
            follow_id=row.follow_id,
            agent_id=row.agent_id,
            target_agent_id=row.target_agent_id,
            created_at=row.created_at,
        ),
        explanation=normalize_action_explanation(row.explanation),
        metadata=build_metadata(row),
    )


def turn_post_snapshot_to_generated(snapshot: TurnPostSnapshot) -> GeneratedPost:
    """Build ``GeneratedPost`` from a persisted ``turn_posts`` row."""
    return GeneratedPost(
        snapshot=snapshot,
        explanation=normalize_action_explanation(snapshot.explanation),
        metadata=_build_generation_metadata(snapshot),
    )
