"""Tests for simulation.core.action_generators.registry module."""

import pytest

from simulation.core.action_generators.interfaces import LikeGenerator
from simulation.core.action_generators.registry import (
    get_like_generator,
)
from simulation.core.action_generators.validators import (
    BEHAVIOR_MODE_DETERMINISTIC,
)


def test_get_like_generator_returns_like_generator():
    """get_like_generator returns a LikeGenerator instance."""
    generator = get_like_generator(BEHAVIOR_MODE_DETERMINISTIC)
    assert isinstance(generator, LikeGenerator)


def test_get_like_generator_caches_instance():
    """Same mode returns cached instance."""
    g1 = get_like_generator(BEHAVIOR_MODE_DETERMINISTIC)
    g2 = get_like_generator(BEHAVIOR_MODE_DETERMINISTIC)
    assert g1 is g2


def test_get_like_generator_unknown_mode_raises():
    """Unknown mode raises ValueError."""
    with pytest.raises(ValueError, match="Unknown behavior mode"):
        get_like_generator("unknown")


def test_default_mode_is_deterministic():
    """get_like_generator() with no args uses deterministic mode."""
    generator = get_like_generator()
    assert isinstance(generator, LikeGenerator)
