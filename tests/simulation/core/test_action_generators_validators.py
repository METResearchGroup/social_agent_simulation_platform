"""Tests for simulation.core.action_generators.validators module."""

import pytest

from simulation.core.action_generators.validators import validate_algorithm


def test_validate_algorithm_accepts_valid_like_algorithm():
    """validate_algorithm accepts deterministic for like."""
    result = validate_algorithm("like", "deterministic")
    assert result == "deterministic"


def test_validate_algorithm_accepts_valid_follow_algorithm():
    """validate_algorithm accepts random_simple for follow."""
    result = validate_algorithm("follow", "random_simple")
    assert result == "random_simple"


def test_validate_algorithm_accepts_valid_comment_algorithm():
    """validate_algorithm accepts random_simple for comment."""
    result = validate_algorithm("comment", "random_simple")
    assert result == "random_simple"


def test_validate_algorithm_unknown_action_type_raises():
    """Unknown action_type raises ValueError."""
    with pytest.raises(ValueError, match="Unknown action_type"):
        validate_algorithm("invalid_action", "random_simple")


def test_validate_algorithm_unknown_algorithm_raises():
    """Unknown algorithm for action type raises ValueError."""
    with pytest.raises(ValueError, match="must be one of"):
        validate_algorithm("like", "unknown")
