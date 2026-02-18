"""Tests for simulation.core.action_generators.registry module."""

import pytest

from simulation.core.action_generators.interfaces import (
    CommentGenerator,
    FollowGenerator,
    LikeGenerator,
)
from simulation.core.action_generators.registry import (
    get_comment_generator,
    get_follow_generator,
    get_like_generator,
)
from simulation.core.action_generators.validators import (
    BEHAVIOR_MODE_DETERMINISTIC,
)


class TestGetLikeGenerator:
    """Tests for get_like_generator function."""

    def test_returns_like_generator(self):
        """get_like_generator returns a LikeGenerator instance."""
        generator = get_like_generator(BEHAVIOR_MODE_DETERMINISTIC)
        assert isinstance(generator, LikeGenerator)

    def test_caches_instance(self):
        """Same mode returns cached instance."""
        g1 = get_like_generator(BEHAVIOR_MODE_DETERMINISTIC)
        g2 = get_like_generator(BEHAVIOR_MODE_DETERMINISTIC)
        assert g1 is g2

    def test_unknown_mode_raises(self):
        """Unknown mode raises ValueError."""
        with pytest.raises(ValueError, match="behavior_mode must be one of"):
            get_like_generator("unknown")

    def test_default_mode_is_deterministic(self):
        """get_like_generator() with no args uses deterministic mode."""
        default_generator = get_like_generator()
        deterministic_generator = get_like_generator(BEHAVIOR_MODE_DETERMINISTIC)
        assert default_generator is deterministic_generator


def test_default_mode_is_deterministic():
    """get_like_generator() with no args uses deterministic mode."""
    default_generator = get_like_generator()
    deterministic_generator = get_like_generator(BEHAVIOR_MODE_DETERMINISTIC)
    assert default_generator is deterministic_generator


def test_get_follow_generator_returns_follow_generator():
    """get_follow_generator returns a FollowGenerator instance."""
    generator = get_follow_generator(BEHAVIOR_MODE_DETERMINISTIC)
    assert isinstance(generator, FollowGenerator)


def test_get_follow_generator_caches_instance():
    """Same mode returns cached follow generator instance."""
    g1 = get_follow_generator(BEHAVIOR_MODE_DETERMINISTIC)
    g2 = get_follow_generator(BEHAVIOR_MODE_DETERMINISTIC)
    assert g1 is g2


def test_get_follow_generator_unknown_mode_raises():
    """Unknown mode raises ValueError."""
    with pytest.raises(ValueError, match="behavior_mode must be one of"):
        get_follow_generator("unknown")


def test_get_follow_generator_default_mode_is_deterministic():
    """get_follow_generator() with no args uses deterministic mode."""
    default_generator = get_follow_generator()
    deterministic_generator = get_follow_generator(BEHAVIOR_MODE_DETERMINISTIC)
    assert default_generator is deterministic_generator


class TestGetCommentGenerator:
    """Tests for get_comment_generator function."""

    def test_returns_comment_generator(self):
        """get_comment_generator returns a CommentGenerator instance."""
        generator = get_comment_generator(BEHAVIOR_MODE_DETERMINISTIC)
        assert isinstance(generator, CommentGenerator)

    def test_caches_instance(self):
        """Same mode returns cached instance."""
        g1 = get_comment_generator(BEHAVIOR_MODE_DETERMINISTIC)
        g2 = get_comment_generator(BEHAVIOR_MODE_DETERMINISTIC)
        assert g1 is g2

    def test_unknown_mode_raises(self):
        """Unknown mode raises ValueError."""
        with pytest.raises(ValueError, match="behavior_mode must be one of"):
            get_comment_generator("unknown")

    def test_default_mode_is_deterministic(self):
        """get_comment_generator() with no args uses deterministic mode."""
        default_generator = get_comment_generator()
        deterministic_generator = get_comment_generator(BEHAVIOR_MODE_DETERMINISTIC)
        assert default_generator is deterministic_generator
