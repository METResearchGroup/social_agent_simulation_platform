"""Factories for naive LLM-powered follow generators."""

from ml_tooling.llm.llm_service import LLMService, get_llm_service
from simulation.core.action_generators.follow.algorithms.naive_llm.algorithm import (
    NaiveLLMFollowGenerator,
)
from simulation.core.action_generators.interfaces import FollowGenerator

__all__ = ["create_naive_llm_follow_generator"]


def create_naive_llm_follow_generator(
    *,
    llm_service: LLMService | None = None,
) -> FollowGenerator:
    """Return a NaiveLLMFollowGenerator wired with the requested LLM service."""
    return NaiveLLMFollowGenerator(llm_service=llm_service or get_llm_service())
