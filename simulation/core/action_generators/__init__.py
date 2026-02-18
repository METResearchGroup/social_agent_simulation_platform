"""Action generators for agent behaviors."""

from simulation.core.action_generators.registry import (
    get_follow_generator,
    get_comment_generator,
    get_like_generator,
)

__all__ = [
    "get_follow_generator",
    "get_comment_generator",
    "get_like_generator",
]
