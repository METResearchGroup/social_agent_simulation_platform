"""Comment-specific action-generator factories."""

from simulation.core.factories.action_generators.comment.naive_llm import (
    create_naive_llm_comment_generator,
)

__all__ = ["create_naive_llm_comment_generator"]
