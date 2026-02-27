"""Factories for naive LLM-powered comment generators."""

from ml_tooling.llm.llm_service import LLMService, get_llm_service
from simulation.core.action_generators.comment.algorithms.naive_llm.algorithm import (
    NaiveLLMCommentGenerator,
)
from simulation.core.action_generators.interfaces import CommentGenerator

__all__ = ["create_naive_llm_comment_generator"]


def create_naive_llm_comment_generator(
    *,
    llm_service: LLMService | None = None,
) -> CommentGenerator:
    """Return a NaiveLLMCommentGenerator wired with the requested LLM service."""
    return NaiveLLMCommentGenerator(llm_service=llm_service or get_llm_service())
