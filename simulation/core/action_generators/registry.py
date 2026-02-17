"""Central registry for action generators.

Single source of truth for behavior mode (e.g. deterministic, llm).
Delegates to per-action algorithm implementations.
"""

from simulation.core.action_generators.interfaces import LikeGenerator
from simulation.core.action_generators.validators import (
    BEHAVIOR_MODE_DETERMINISTIC,
    DEFAULT_BEHAVIOR_MODE,
    validate_behavior_mode,
)

_like_generator_cache: dict[str, LikeGenerator] = {}


def get_like_generator(mode: str = DEFAULT_BEHAVIOR_MODE) -> LikeGenerator:
    """Return a LikeGenerator for the given behavior mode."""
    validate_behavior_mode(mode)
    if mode not in _like_generator_cache:
        _like_generator_cache[mode] = _create_like_generator(mode)
    return _like_generator_cache[mode]


def _create_like_generator(mode: str) -> LikeGenerator:
    if mode == BEHAVIOR_MODE_DETERMINISTIC:
        from simulation.core.action_generators.like.algorithms.deterministic import (
            DeterministicLikeGenerator,
        )

        return DeterministicLikeGenerator()
    raise ValueError(f"Unsupported like generator mode: {mode}")
