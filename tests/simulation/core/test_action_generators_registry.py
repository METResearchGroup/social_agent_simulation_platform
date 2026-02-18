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


class TestGetLikeGenerator:
    """Tests for get_like_generator function."""

    def test_returns_like_generator(self):
        """get_like_generator returns a LikeGenerator instance."""
        generator = get_like_generator(algorithm="deterministic")
        assert isinstance(generator, LikeGenerator)

    def test_caches_instance(self):
        """Same algorithm returns cached instance."""
        g1 = get_like_generator(algorithm="deterministic")
        g2 = get_like_generator(algorithm="deterministic")
        assert g1 is g2

    def test_unknown_algorithm_raises(self):
        """Unknown algorithm raises ValueError."""
        with pytest.raises(ValueError, match="must be one of"):
            get_like_generator(algorithm="unknown")

    def test_default_uses_config_deterministic(self):
        """get_like_generator() with no args uses config default (deterministic)."""
        default_generator = get_like_generator()
        explicit_generator = get_like_generator(algorithm="deterministic")
        assert default_generator is explicit_generator


def test_get_like_generator_default_uses_config():
    """get_like_generator() with no args uses config default."""
    default_generator = get_like_generator()
    deterministic_generator = get_like_generator(algorithm="deterministic")
    assert default_generator is deterministic_generator


def test_get_follow_generator_returns_follow_generator():
    """get_follow_generator returns a FollowGenerator instance."""
    generator = get_follow_generator(algorithm="random_simple")
    assert isinstance(generator, FollowGenerator)


def test_get_follow_generator_caches_instance():
    """Same algorithm returns cached follow generator instance."""
    g1 = get_follow_generator(algorithm="random_simple")
    g2 = get_follow_generator(algorithm="random_simple")
    assert g1 is g2


def test_get_follow_generator_unknown_algorithm_raises():
    """Unknown algorithm raises ValueError."""
    with pytest.raises(ValueError, match="must be one of"):
        get_follow_generator(algorithm="unknown")


def test_get_follow_generator_default_uses_config():
    """get_follow_generator() with no args uses config default (random_simple)."""
    default_generator = get_follow_generator()
    explicit_generator = get_follow_generator(algorithm="random_simple")
    assert default_generator is explicit_generator


class TestGetCommentGenerator:
    """Tests for get_comment_generator function."""

    def test_returns_comment_generator(self):
        """get_comment_generator returns a CommentGenerator instance."""
        generator = get_comment_generator(algorithm="random_simple")
        assert isinstance(generator, CommentGenerator)

    def test_caches_instance(self):
        """Same algorithm returns cached instance."""
        g1 = get_comment_generator(algorithm="random_simple")
        g2 = get_comment_generator(algorithm="random_simple")
        assert g1 is g2

    def test_unknown_algorithm_raises(self):
        """Unknown algorithm raises ValueError."""
        with pytest.raises(ValueError, match="must be one of"):
            get_comment_generator(algorithm="unknown")

    def test_default_uses_config_random_simple(self):
        """get_comment_generator() with no args uses config default (random_simple)."""
        default_generator = get_comment_generator()
        explicit_generator = get_comment_generator(algorithm="random_simple")
        assert default_generator is explicit_generator
