"""Naive LLM like generation algorithm.

Uses a single LLM call to predict which posts the user would like.
"""

from __future__ import annotations

import logging

from lib.timestamp_utils import get_current_timestamp
from ml_tooling.llm.llm_service import LLMService, get_llm_service
from simulation.core.action_generators.interfaces import LikeGenerator
from simulation.core.action_generators.like.algorithms.naive_llm.prompt import (
    LIKE_PROMPT,
)
from simulation.core.action_generators.like.algorithms.naive_llm.response_models import (
    LikePrediction,
)
from simulation.core.action_generators.utils.llm_utils import (
    _posts_to_minimal_json,
    _resolve_model_used,
)
from simulation.core.models.actions import Like
from simulation.core.models.generated.base import GenerationMetadata
from simulation.core.models.generated.like import GeneratedLike
from simulation.core.models.posts import BlueskyFeedPost

logger = logging.getLogger(__name__)
EXPLANATION: str = "LLM prediction (naive_llm)"
LIKE_POLICY: str = "naive_llm"


def _build_prompt(agent_handle: str, candidates: list[BlueskyFeedPost]) -> str:
    """Build the like prediction prompt."""
    posts_json = _posts_to_minimal_json(candidates)
    return LIKE_PROMPT.format(agent_handle=agent_handle, posts_json=posts_json)


def _build_generated_like(
    *,
    post: BlueskyFeedPost,
    agent_handle: str,
    run_id: str,
    turn_number: int,
    model_used: str | None,
) -> GeneratedLike:
    """Build a GeneratedLike with IDs and metadata."""
    post_id = post.id
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
            model_used=model_used,
            generation_metadata={"policy": LIKE_POLICY},
            created_at=created_at,
        ),
    )


class NaiveLLMLikeGenerator(LikeGenerator):
    """Generates likes using LLM prediction."""

    def __init__(self, llm_service: LLMService | None = None) -> None:
        """Initialize with optional LLM service for testing."""
        self._llm = llm_service if llm_service is not None else get_llm_service()

    def generate(
        self,
        *,
        candidates: list[BlueskyFeedPost],
        run_id: str,
        turn_number: int,
        agent_handle: str,
    ) -> list[GeneratedLike]:
        """Generate likes from candidates using LLM prediction."""
        if not candidates:
            logger.warning(
                "naive_llm like generator: no candidates provided (OK if expected)"
            )
            return []

        prompt = _build_prompt(agent_handle=agent_handle, candidates=candidates)
        response: LikePrediction = self._llm.structured_completion(
            messages=[{"role": "user", "content": prompt}],
            response_model=LikePrediction,
        )

        valid_ids = {p.id for p in candidates}
        post_by_id = {p.id: p for p in candidates}
        to_like_ids = [pid for pid in response.post_ids if pid in valid_ids]

        model_used = _resolve_model_used()
        generated: list[GeneratedLike] = [
            _build_generated_like(
                post=post_by_id[pid],
                agent_handle=agent_handle,
                run_id=run_id,
                turn_number=turn_number,
                model_used=model_used,
            )
            for pid in to_like_ids
        ]
        generated.sort(key=lambda g: g.like.post_id)
        return generated
