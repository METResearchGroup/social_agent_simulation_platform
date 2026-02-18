"""Action generators for agent behaviors."""

from simulation.core.action_generators.registry import (
    get_comment_generator,
    get_like_generator,
)

__all__ = [
    "get_comment_generator",
    "get_like_generator",
]
