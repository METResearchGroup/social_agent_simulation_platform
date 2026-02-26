"""Factories for action generators.

These factories are a composition root for algorithm implementations that need
concrete infrastructure (e.g., global LLM providers). Non-factory code must
accept dependencies as required inputs and must not self-wire defaults.
"""

from ml_tooling.llm.llm_service import LLMService, get_llm_service
from simulation.core.action_generators.comment.algorithms.naive_llm.algorithm import (
    NaiveLLMCommentGenerator,
)
from simulation.core.action_generators.follow.algorithms.naive_llm.algorithm import (
    NaiveLLMFollowGenerator,
)
from simulation.core.action_generators.interfaces import (
    CommentGenerator,
    FollowGenerator,
    LikeGenerator,
)
from simulation.core.action_generators.like.algorithms.naive_llm.algorithm import (
    NaiveLLMLikeGenerator,
)


def create_naive_llm_like_generator(
    *,
    llm_service: LLMService | None = None,
) -> LikeGenerator:
    return NaiveLLMLikeGenerator(llm_service=llm_service or get_llm_service())


def create_naive_llm_comment_generator(
    *,
    llm_service: LLMService | None = None,
) -> CommentGenerator:
    return NaiveLLMCommentGenerator(llm_service=llm_service or get_llm_service())


def create_naive_llm_follow_generator(
    *,
    llm_service: LLMService | None = None,
) -> FollowGenerator:
    return NaiveLLMFollowGenerator(llm_service=llm_service or get_llm_service())
