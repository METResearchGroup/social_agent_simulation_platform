"""Tests for simulation.core.action_generators.config module."""

from unittest.mock import patch

from simulation.core.action_generators.config import resolve_algorithm


class TestResolveAlgorithm:
    """Tests for resolve_algorithm function."""

    def test_explicit_algorithm_overrides_config(self):
        """Explicit algorithm is returned unchanged."""
        result = resolve_algorithm("like", "random_simple")
        assert result == "random_simple"

    def test_explicit_algorithm_for_follow(self):
        """Explicit algorithm for follow is returned unchanged."""
        result = resolve_algorithm("follow", "random_simple")
        assert result == "random_simple"

    def test_none_uses_config_default_when_present(self):
        """When algorithm is None, config default is used."""
        result = resolve_algorithm("like", None)
        assert result == "random_simple"
        result = resolve_algorithm("comment", None)
        assert result == "random_simple"
        result = resolve_algorithm("follow", None)
        assert result == "random_simple"

    def test_empty_string_uses_config_or_fallback(self):
        """Empty string is treated like None, uses config or fallback."""
        result = resolve_algorithm("like", "")
        assert result == "random_simple"
        result = resolve_algorithm("follow", "")
        assert result == "random_simple"

    def test_none_uses_fallback_when_config_missing(self):
        """When config returns empty, fallback is used."""
        with patch(
            "simulation.core.action_generators.config._load",
            return_value={},
        ):
            result = resolve_algorithm("like", None)
        assert result == "random_simple"
        with patch(
            "simulation.core.action_generators.config._load",
            return_value={},
        ):
            result = resolve_algorithm("follow", None)
        assert result == "random_simple"

    def test_none_uses_fallback_when_action_type_absent(self):
        """When config has no entry for action_type, fallback is used."""
        with patch(
            "simulation.core.action_generators.config._load",
            return_value={"other": {"default_algorithm": "other_algo"}},
        ):
            result = resolve_algorithm("like", None)
        assert result == "random_simple"
