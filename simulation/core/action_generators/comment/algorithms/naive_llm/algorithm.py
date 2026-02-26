"""Naive LLM comment generation algorithm.

Uses a single LLM call to predict what comments the user would make.
"""

from __future__ import annotations

import logging

from lib.timestamp_utils import get_current_timestamp
from ml_tooling.llm.llm_service import LLMService
from simulation.core.action_generators.comment.algorithms.naive_llm.prompt import (
    COMMENT_PROMPT,
)
from simulation.core.action_generators.comment.algorithms.naive_llm.response_models import (
    CommentPrediction,
)
from simulation.core.action_generators.interfaces import CommentGenerator
from simulation.core.action_generators.utils.llm_utils import (
    _posts_to_minimal_json,
    _resolve_model_used,
)
from simulation.core.models.actions import Comment
from simulation.core.models.generated.base import GenerationMetadata
from simulation.core.models.generated.comment import GeneratedComment
from simulation.core.models.posts import BlueskyFeedPost

logger = logging.getLogger(__name__)
EXPLANATION: str = "LLM prediction (naive_llm)"
COMMENT_POLICY: str = "naive_llm"


def _build_prompt(agent_handle: str, candidates: list[BlueskyFeedPost]) -> str:
    """Build the comment prediction prompt."""
    posts_json = _posts_to_minimal_json(candidates)
    return COMMENT_PROMPT.format(agent_handle=agent_handle, posts_json=posts_json)


def _build_generated_comment(
    *,
    post: BlueskyFeedPost,
    agent_handle: str,
    run_id: str,
    turn_number: int,
    text: str,
    model_used: str | None,
) -> GeneratedComment:
    """Build a GeneratedComment with IDs and metadata."""
    post_id = post.id
    comment_id = f"comment_{run_id}_{turn_number}_{agent_handle}_{post_id}"
    created_at = get_current_timestamp()
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
            model_used=model_used,
            generation_metadata={"policy": COMMENT_POLICY},
            created_at=created_at,
        ),
    )


class NaiveLLMCommentGenerator(CommentGenerator):
    """Generates comments using LLM prediction."""

    def __init__(self, *, llm_service: LLMService) -> None:
        """Initialize with injected LLM service."""
        self._llm = llm_service

    def generate(
        self,
        *,
        candidates: list[BlueskyFeedPost],
        run_id: str,
        turn_number: int,
        agent_handle: str,
    ) -> list[GeneratedComment]:
        """Generate comments from candidates using LLM prediction."""
        if not candidates:
            logger.warning(
                "naive_llm comment generator: no candidates provided (OK if expected)"
            )
            return []

        prompt = _build_prompt(agent_handle=agent_handle, candidates=candidates)
        response: CommentPrediction = self._llm.structured_completion(
            messages=[{"role": "user", "content": prompt}],
            response_model=CommentPrediction,
        )

        valid_ids = {p.id for p in candidates}
        post_by_id = {p.id: p for p in candidates}
        model_used = _resolve_model_used()

        generated: list[GeneratedComment] = []

        already_included_post_ids = set()
        for item in response.comments:
            if (
                item.post_id in already_included_post_ids
                or item.post_id not in valid_ids
            ):
                continue
            already_included_post_ids.add(item.post_id)
            post = post_by_id[item.post_id]
            generated.append(
                _build_generated_comment(
                    post=post,
                    agent_handle=agent_handle,
                    run_id=run_id,
                    turn_number=turn_number,
                    text=item.text,
                    model_used=model_used,
                )
            )
        generated.sort(key=lambda c: c.comment.post_id)
        return generated
