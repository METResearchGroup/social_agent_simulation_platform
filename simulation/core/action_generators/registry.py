"""Central registry for action generators.

Single source of truth for behavior mode (e.g. default, llm).
Delegates to per-action algorithm implementations.
"""

from simulation.core.action_generators.interfaces import (
    CommentGenerator,
    FollowGenerator,
    LikeGenerator,
)
from simulation.core.action_generators.validators import (
    BEHAVIOR_MODE_DETERMINISTIC,
    DEFAULT_BEHAVIOR_MODE,
    validate_behavior_mode,
)

_like_generator_cache: dict[str, LikeGenerator] = {}
_follow_generator_cache: dict[str, FollowGenerator] = {}
_comment_generator_cache: dict[str, CommentGenerator] = {}


def get_like_generator(mode: str = DEFAULT_BEHAVIOR_MODE) -> LikeGenerator:
    """Return a LikeGenerator for the given behavior mode."""
    validate_behavior_mode(mode)
    if mode not in _like_generator_cache:
        _like_generator_cache[mode] = _create_like_generator(mode)
    return _like_generator_cache[mode]


def get_follow_generator(mode: str = DEFAULT_BEHAVIOR_MODE) -> FollowGenerator:
    """Return a FollowGenerator for the given behavior mode."""
    validate_behavior_mode(mode)
    if mode not in _follow_generator_cache:
        _follow_generator_cache[mode] = _create_follow_generator(mode)
    return _follow_generator_cache[mode]


def get_comment_generator(mode: str = DEFAULT_BEHAVIOR_MODE) -> CommentGenerator:
    """Return a CommentGenerator for the given behavior mode."""
    validate_behavior_mode(mode)
    if mode not in _comment_generator_cache:
        _comment_generator_cache[mode] = _create_comment_generator(mode)
    return _comment_generator_cache[mode]


def _create_like_generator(mode: str) -> LikeGenerator:
    from lib.validation_utils import validate_value_in_set
    from simulation.core.action_generators.validators import BEHAVIOR_MODES

    validate_value_in_set(
        mode,
        "like_generator_mode",
        BEHAVIOR_MODES,
        allowed_display_name=str(BEHAVIOR_MODES),
    )
    if mode == BEHAVIOR_MODE_DETERMINISTIC:
        from simulation.core.action_generators.like.algorithms.deterministic import (
            DeterministicLikeGenerator,
        )

        return DeterministicLikeGenerator()
    raise ValueError(f"Unsupported like generator mode: {mode}")


def _create_follow_generator(mode: str) -> FollowGenerator:
    from lib.validation_utils import validate_value_in_set
    from simulation.core.action_generators.validators import BEHAVIOR_MODES

    validate_value_in_set(
        mode,
        "follow_generator_mode",
        BEHAVIOR_MODES,
        allowed_display_name=str(BEHAVIOR_MODES),
    )
    if mode == BEHAVIOR_MODE_DETERMINISTIC:
        from simulation.core.action_generators.follow.algorithms.deterministic import (
            DeterministicFollowGenerator,
        )

        return DeterministicFollowGenerator()
    raise ValueError(f"Unsupported follow generator mode: {mode}")


def _create_comment_generator(mode: str) -> CommentGenerator:
    from lib.validation_utils import validate_value_in_set
    from simulation.core.action_generators.validators import BEHAVIOR_MODES

    validate_value_in_set(
        mode,
        "comment_generator_mode",
        BEHAVIOR_MODES,
        allowed_display_name=str(BEHAVIOR_MODES),
    )
    if mode == BEHAVIOR_MODE_DETERMINISTIC:
        from simulation.core.action_generators.comment.algorithms.random_simple import (
            RandomSimpleCommentGenerator,
        )

        return RandomSimpleCommentGenerator()
    raise ValueError(f"Unsupported comment generator mode: {mode}")
