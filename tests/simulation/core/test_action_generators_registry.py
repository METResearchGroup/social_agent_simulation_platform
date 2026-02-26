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
        generator = get_like_generator(algorithm="random_simple")
        expected_result = LikeGenerator
        assert isinstance(generator, expected_result)

    def test_caches_instance(self):
        """Same algorithm returns cached instance."""
        g1 = get_like_generator(algorithm="random_simple")
        g2 = get_like_generator(algorithm="random_simple")
        expected_result = g1
        assert g2 is expected_result

    def test_unknown_algorithm_raises(self):
        """Unknown algorithm raises ValueError."""
        expected_result = "must be one of"
        with pytest.raises(ValueError, match=expected_result):
            get_like_generator(algorithm="unknown")

    def test_default_uses_config_random_simple(self):
        """get_like_generator() with no args uses config default (random_simple)."""
        default_generator = get_like_generator()
        explicit_generator = get_like_generator(algorithm="random_simple")
        expected_result = explicit_generator
        assert default_generator is expected_result

    def test_get_like_generator_naive_llm(self):
        """get_like_generator returns NaiveLLMLikeGenerator for naive_llm."""
        generator = get_like_generator(algorithm="naive_llm")
        expected_result = LikeGenerator
        assert isinstance(generator, expected_result)
        expected_result = "NaiveLLMLikeGenerator"
        assert generator.__class__.__name__ == expected_result


def test_get_follow_generator_returns_follow_generator():
    """get_follow_generator returns a FollowGenerator instance."""
    generator = get_follow_generator(algorithm="random_simple")
    expected_result = FollowGenerator
    assert isinstance(generator, expected_result)


def test_get_follow_generator_caches_instance():
    """Same algorithm returns cached follow generator instance."""
    g1 = get_follow_generator(algorithm="random_simple")
    g2 = get_follow_generator(algorithm="random_simple")
    expected_result = g1
    assert g2 is expected_result


def test_get_follow_generator_unknown_algorithm_raises():
    """Unknown algorithm raises ValueError."""
    expected_result = "must be one of"
    with pytest.raises(ValueError, match=expected_result):
        get_follow_generator(algorithm="unknown")


def test_get_follow_generator_default_uses_config():
    """get_follow_generator() with no args uses config default (random_simple)."""
    default_generator = get_follow_generator()
    explicit_generator = get_follow_generator(algorithm="random_simple")
    expected_result = explicit_generator
    assert default_generator is expected_result


def test_get_follow_generator_naive_llm():
    """get_follow_generator returns NaiveLLMFollowGenerator for naive_llm."""
    generator = get_follow_generator(algorithm="naive_llm")
    expected_result = FollowGenerator
    assert isinstance(generator, expected_result)
    expected_result = "NaiveLLMFollowGenerator"
    assert generator.__class__.__name__ == expected_result


class TestGetCommentGenerator:
    """Tests for get_comment_generator function."""

    def test_returns_comment_generator(self):
        """get_comment_generator returns a CommentGenerator instance."""
        generator = get_comment_generator(algorithm="random_simple")
        expected_result = CommentGenerator
        assert isinstance(generator, expected_result)

    def test_caches_instance(self):
        """Same algorithm returns cached instance."""
        g1 = get_comment_generator(algorithm="random_simple")
        g2 = get_comment_generator(algorithm="random_simple")
        expected_result = g1
        assert g2 is expected_result

    def test_unknown_algorithm_raises(self):
        """Unknown algorithm raises ValueError."""
        expected_result = "must be one of"
        with pytest.raises(ValueError, match=expected_result):
            get_comment_generator(algorithm="unknown")

    def test_default_uses_config_random_simple(self):
        """get_comment_generator() with no args uses config default (random_simple)."""
        default_generator = get_comment_generator()
        explicit_generator = get_comment_generator(algorithm="random_simple")
        expected_result = explicit_generator
        assert default_generator is expected_result

    def test_get_comment_generator_naive_llm(self):
        """get_comment_generator returns NaiveLLMCommentGenerator for naive_llm."""
        generator = get_comment_generator(algorithm="naive_llm")
        expected_result = CommentGenerator
        assert isinstance(generator, expected_result)
        expected_result = "NaiveLLMCommentGenerator"
        assert generator.__class__.__name__ == expected_result
