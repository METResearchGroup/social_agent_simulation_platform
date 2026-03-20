"""Naive LLM follow generation algorithm.

Uses a single LLM call to predict who the user would follow.
"""

from __future__ import annotations

import json
import logging

from lib.timestamp_utils import get_current_timestamp
from ml_tooling.llm.llm_service import LLMService
from simulation.core.action_generators.follow.algorithms.naive_llm.prompt import (
    FOLLOW_PROMPT,
)
from simulation.core.action_generators.follow.algorithms.naive_llm.response_models import (
    FollowPrediction,
)
from simulation.core.action_generators.follow.utils import derive_target_agent_id
from simulation.core.action_generators.interfaces import FollowGenerator
from simulation.core.action_generators.mixins.llm_action_generator_mixin import (
    LLMActionGeneratorMixin,
)
from simulation.core.action_generators.utils.llm_utils import _resolve_model_used
from simulation.core.models.actions import Follow
from simulation.core.models.generated.base import GenerationMetadata
from simulation.core.models.generated.follow import GeneratedFollow
from simulation.core.models.posts import Post

logger = logging.getLogger(__name__)
EXPLANATION: str = "LLM prediction (naive_llm)"
FOLLOW_POLICY: str = "naive_llm"


def _collect_unique_authors(
    candidates: list[Post],
    agent_handle: str,
) -> dict[str, Post]:
    """Return one post per author (excluding self), keyed by author_handle."""
    result: dict[str, Post] = {}
    for post in candidates:
        author_handle = post.author_handle
        if author_handle == agent_handle:
            continue
        if (
            author_handle not in result
            or post.created_at > result[author_handle].created_at
        ):
            result[author_handle] = post
    return result


def _authors_to_minimal_json(author_to_post: dict[str, Post]) -> str:
    """Serialize authors to minimal JSON for the prompt."""
    items = [
        {
            "author_handle": handle,
            "like_count": post.like_count,
        }
        for handle, post in sorted(author_to_post.items())
    ]
    return json.dumps(items, indent=2)


def _build_prompt(
    agent_handle: str,
    author_to_post: dict[str, Post],
) -> str:
    """Build the follow prediction prompt."""
    authors_json = _authors_to_minimal_json(author_to_post)
    return FOLLOW_PROMPT.format(
        agent_handle=agent_handle,
        authors_json=authors_json,
    )


def _build_generated_follow(
    *,
    post: Post,
    agent_handle: str,
    agent_id: str,
    run_id: str,
    turn_number: int,
    model_used: str | None,
) -> GeneratedFollow:
    """Build a GeneratedFollow with IDs and metadata."""
    target_agent_id = derive_target_agent_id(post)
    follow_id = f"follow_{run_id}_{turn_number}_{agent_handle}_{target_agent_id}"
    created_at = get_current_timestamp()
    return GeneratedFollow(
        follow=Follow(
            follow_id=follow_id,
            agent_id=agent_id,
            target_agent_id=target_agent_id,
            created_at=created_at,
        ),
        explanation=EXPLANATION,
        metadata=GenerationMetadata(
            model_used=model_used,
            generation_metadata={"policy": FOLLOW_POLICY},
            created_at=created_at,
        ),
    )


class NaiveLLMFollowGenerator(LLMActionGeneratorMixin, FollowGenerator):
    """Generates follows using LLM prediction."""

    def __init__(self, *, llm_service: LLMService) -> None:
        """Initialize with injected LLM service."""
        super().__init__(llm_service=llm_service)

    def generate(
        self,
        *,
        candidates: list[Post],
        run_id: str,
        turn_number: int,
        agent_handle: str,
        agent_id: str,
    ) -> list[GeneratedFollow]:
        """Generate follows from candidates using LLM prediction."""
        if not candidates:
            logger.warning(
                "naive_llm follow generator: no candidates provided (OK if expected)"
            )
            return []

        author_to_post = _collect_unique_authors(candidates, agent_handle)
        if not author_to_post:
            return []

        prompt = _build_prompt(agent_handle=agent_handle, author_to_post=author_to_post)
        response: FollowPrediction = self._call_llm(
            prompt=prompt, response_model=FollowPrediction
        )

        to_follow_ids = self._filter_and_dedupe_ids(
            response_ids=response.user_ids,
            valid_ids=set(author_to_post.keys()),
        )

        model_used = _resolve_model_used()

        generated: list[GeneratedFollow] = [
            _build_generated_follow(
                post=author_to_post[uid],
                agent_handle=agent_handle,
                agent_id=agent_id,
                run_id=run_id,
                turn_number=turn_number,
                model_used=model_used,
            )
            for uid in to_follow_ids
        ]
        generated.sort(key=lambda g: g.follow.target_agent_id)
        return generated
