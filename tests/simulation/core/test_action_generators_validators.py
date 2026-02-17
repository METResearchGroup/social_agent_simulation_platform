"""Tests for simulation.core.action_generators.validators module."""

import pytest

from simulation.core.action_generators.validators import (
    BEHAVIOR_MODE_DETERMINISTIC,
    validate_behavior_mode,
)


def test_validate_behavior_mode_accepts_deterministic():
    """validate_behavior_mode accepts deterministic mode."""
    result = validate_behavior_mode(BEHAVIOR_MODE_DETERMINISTIC)
    assert result == BEHAVIOR_MODE_DETERMINISTIC


def test_validate_behavior_mode_unknown_raises():
    """Unknown mode raises ValueError."""
    with pytest.raises(ValueError, match="Unknown behavior mode"):
        validate_behavior_mode("unknown")
