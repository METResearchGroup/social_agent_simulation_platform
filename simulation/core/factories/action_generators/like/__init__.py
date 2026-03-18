"""Like-specific action-generator factories."""

from simulation.core.factories.action_generators.like.naive_llm import (
    create_naive_llm_like_generator,
)

__all__ = ["create_naive_llm_like_generator"]
