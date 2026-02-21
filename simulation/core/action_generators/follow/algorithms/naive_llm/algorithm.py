"""Naive LLM follow generation algorithm.

Uses a single LLM call to predict who the user would follow.
"""

from __future__ import annotations

import json
import logging

from lib.timestamp_utils import get_current_timestamp
from ml_tooling.llm.llm_service import LLMService, get_llm_service
from simulation.core.action_generators.follow.algorithms.naive_llm.prompt import (
    FOLLOW_PROMPT,
)
from simulation.core.action_generators.follow.algorithms.naive_llm.response_models import (
    FollowPrediction,
)
from simulation.core.action_generators.interfaces import FollowGenerator
from simulation.core.action_generators.utils.llm_utils import _resolve_model_used
from simulation.core.models.actions import Follow
from simulation.core.models.generated.base import GenerationMetadata
from simulation.core.models.generated.follow import GeneratedFollow
from simulation.core.models.posts import BlueskyFeedPost

logger = logging.getLogger(__name__)
EXPLANATION: str = "LLM prediction (naive_llm)"
FOLLOW_POLICY: str = "naive_llm"


def _collect_unique_authors(
    candidates: list[BlueskyFeedPost],
    agent_handle: str,
) -> dict[str, BlueskyFeedPost]:
    """Return one post per author (excluding self), keyed by author_handle."""
    result: dict[str, BlueskyFeedPost] = {}
    for post in candidates:
        author_handle = post.author_handle
        if author_handle == agent_handle:
            continue
        if author_handle not in result:
            result[author_handle] = post
        # select the most recent post for each author (newest first)
        elif post.created_at > result[author_handle].created_at:
            result[author_handle] = post
    return result


def _authors_to_minimal_json(author_to_post: dict[str, BlueskyFeedPost]) -> str:
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
    author_to_post: dict[str, BlueskyFeedPost],
) -> str:
    """Build the follow prediction prompt."""
    authors_json = _authors_to_minimal_json(author_to_post)
    return FOLLOW_PROMPT.format(
        agent_handle=agent_handle,
        authors_json=authors_json,
    )


def _build_generated_follow(
    *,
    post: BlueskyFeedPost,
    agent_handle: str,
    run_id: str,
    turn_number: int,
    model_used: str | None,
) -> GeneratedFollow:
    """Build a GeneratedFollow with IDs and metadata."""
    user_id = post.author_handle
    follow_id = f"follow_{run_id}_{turn_number}_{agent_handle}_{user_id}"
    created_at = get_current_timestamp()
    return GeneratedFollow(
        follow=Follow(
            follow_id=follow_id,
            agent_id=agent_handle,
            user_id=user_id,
            created_at=created_at,
        ),
        explanation=EXPLANATION,
        metadata=GenerationMetadata(
            model_used=model_used,
            generation_metadata={"policy": FOLLOW_POLICY},
            created_at=created_at,
        ),
    )


def _deduplicate_follow_ids(candidate_follow_ids: list[str]) -> list[str]:
    already_included_user_ids = set()
    to_follow_ids = []
    for uid in candidate_follow_ids:
        if uid in already_included_user_ids:
            continue
        already_included_user_ids.add(uid)
        to_follow_ids.append(uid)
    return to_follow_ids


def _get_ids_to_follow(
    *,
    response_user_ids: list[str],
    valid_user_ids: set[str],
) -> list[str]:
    candidate_follow_ids = [uid for uid in response_user_ids if uid in valid_user_ids]
    return _deduplicate_follow_ids(candidate_follow_ids)


class NaiveLLMFollowGenerator(FollowGenerator):
    """Generates follows using LLM prediction."""

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
        response: FollowPrediction = self._llm.structured_completion(
            messages=[{"role": "user", "content": prompt}],
            response_model=FollowPrediction,
        )

        to_follow_ids = _get_ids_to_follow(
            response_user_ids=response.user_ids,
            valid_user_ids=set(author_to_post.keys()),
        )

        model_used = _resolve_model_used()

        generated: list[GeneratedFollow] = [
            _build_generated_follow(
                post=author_to_post[uid],
                agent_handle=agent_handle,
                run_id=run_id,
                turn_number=turn_number,
                model_used=model_used,
            )
            for uid in to_follow_ids
        ]
        generated.sort(key=lambda g: g.follow.user_id)
        return generated
