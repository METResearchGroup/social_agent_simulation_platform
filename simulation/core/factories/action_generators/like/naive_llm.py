"""Factories for naive LLM-powered like generators."""

from ml_tooling.llm.llm_service import LLMService, get_llm_service
from simulation.core.action_generators.interfaces import LikeGenerator
from simulation.core.action_generators.like.algorithms.naive_llm.algorithm import (
    NaiveLLMLikeGenerator,
)

__all__ = ["create_naive_llm_like_generator"]


def create_naive_llm_like_generator(
    *,
    llm_service: LLMService | None = None,
) -> LikeGenerator:
    """Return a NaiveLLMLikeGenerator wired with the requested LLM service."""
    return NaiveLLMLikeGenerator(llm_service=llm_service or get_llm_service())
