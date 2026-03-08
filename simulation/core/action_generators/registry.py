"""Central registry for action generators.

Single source of truth for per-action algorithms. Delegates to per-action
algorithm implementations. Uses config.yaml for default algorithms when
algorithm is omitted.
"""

from collections.abc import Callable

from simulation.core.action_generators.config import resolve_algorithm
from simulation.core.action_generators.interfaces import (
    CommentGenerator,
    FollowGenerator,
    LikeGenerator,
)
from simulation.core.action_generators.validators import (
    COMMENT_ALGORITHMS,
    FOLLOW_ALGORITHMS,
    LIKE_ALGORITHMS,
    validate_algorithm,
)


def _create_random_simple_like() -> LikeGenerator:
    from simulation.core.action_generators.like.algorithms.random_simple import (
        RandomSimpleLikeGenerator,
    )

    return RandomSimpleLikeGenerator()


def _create_random_simple_follow() -> FollowGenerator:
    from simulation.core.action_generators.follow.algorithms.random_simple import (
        RandomSimpleFollowGenerator,
    )

    return RandomSimpleFollowGenerator()


def _create_random_simple_comment() -> CommentGenerator:
    from simulation.core.action_generators.comment.algorithms.random_simple import (
        RandomSimpleCommentGenerator,
    )

    return RandomSimpleCommentGenerator()


def _create_naive_llm_like() -> LikeGenerator:
    from simulation.core.factories.action_generators.like.naive_llm import (
        create_naive_llm_like_generator,
    )

    return create_naive_llm_like_generator()


def _create_naive_llm_follow() -> FollowGenerator:
    from simulation.core.factories.action_generators.follow.naive_llm import (
        create_naive_llm_follow_generator,
    )

    return create_naive_llm_follow_generator()


def _create_naive_llm_comment() -> CommentGenerator:
    from simulation.core.factories.action_generators.comment.naive_llm import (
        create_naive_llm_comment_generator,
    )

    return create_naive_llm_comment_generator()


_LIKE_ALGORITHM_FACTORIES: dict[str, Callable[[], LikeGenerator]] = {
    "random_simple": _create_random_simple_like,
    "naive_llm": _create_naive_llm_like,
}
assert set(_LIKE_ALGORITHM_FACTORIES.keys()) == set(LIKE_ALGORITHMS)

_FOLLOW_ALGORITHM_FACTORIES: dict[str, Callable[[], FollowGenerator]] = {
    "random_simple": _create_random_simple_follow,
    "naive_llm": _create_naive_llm_follow,
}
assert set(_FOLLOW_ALGORITHM_FACTORIES.keys()) == set(FOLLOW_ALGORITHMS)

_COMMENT_ALGORITHM_FACTORIES: dict[str, Callable[[], CommentGenerator]] = {
    "random_simple": _create_random_simple_comment,
    "naive_llm": _create_naive_llm_comment,
}
assert set(_COMMENT_ALGORITHM_FACTORIES.keys()) == set(COMMENT_ALGORITHMS)

_like_generator_cache: dict[str, LikeGenerator] = {}
_follow_generator_cache: dict[str, FollowGenerator] = {}
_comment_generator_cache: dict[str, CommentGenerator] = {}


def get_like_generator(algorithm: str | None = None) -> LikeGenerator:
    """Return a LikeGenerator. Uses config default when algorithm is omitted."""
    resolved: str = resolve_algorithm("like", algorithm)
    validate_algorithm("like", resolved)
    if resolved not in _like_generator_cache:
        _like_generator_cache[resolved] = _create_like_generator(resolved)
    return _like_generator_cache[resolved]


def get_follow_generator(algorithm: str | None = None) -> FollowGenerator:
    """Return a FollowGenerator. Uses config default when algorithm is omitted."""
    resolved: str = resolve_algorithm("follow", algorithm)
    validate_algorithm("follow", resolved)
    if resolved not in _follow_generator_cache:
        _follow_generator_cache[resolved] = _create_follow_generator(resolved)
    return _follow_generator_cache[resolved]


def get_comment_generator(algorithm: str | None = None) -> CommentGenerator:
    """Return a CommentGenerator. Uses config default when algorithm is omitted."""
    resolved: str = resolve_algorithm("comment", algorithm)
    validate_algorithm("comment", resolved)
    if resolved not in _comment_generator_cache:
        _comment_generator_cache[resolved] = _create_comment_generator(resolved)
    return _comment_generator_cache[resolved]


def _create_like_generator(algorithm: str) -> LikeGenerator:
    factory = _LIKE_ALGORITHM_FACTORIES.get(algorithm)
    if factory is None:
        raise ValueError(f"Unsupported like algorithm: {algorithm}")
    return factory()


def _create_follow_generator(algorithm: str) -> FollowGenerator:
    factory = _FOLLOW_ALGORITHM_FACTORIES.get(algorithm)
    if factory is None:
        raise ValueError(f"Unsupported follow algorithm: {algorithm}")
    return factory()


def _create_comment_generator(algorithm: str) -> CommentGenerator:
    factory = _COMMENT_ALGORITHM_FACTORIES.get(algorithm)
    if factory is None:
        raise ValueError(f"Unsupported comment algorithm: {algorithm}")
    return factory()
