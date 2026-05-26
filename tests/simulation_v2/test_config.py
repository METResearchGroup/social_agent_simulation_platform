"""Tests for simulation_v2 local configuration models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from simulation_v2.config import LocalSimulationConfig


class TestLocalSimulationConfigDefaults:
    def test_default_factory_matches_constructor(self) -> None:
        assert LocalSimulationConfig.default() == LocalSimulationConfig()

    def test_seed_defaults(self) -> None:
        config = LocalSimulationConfig.default()

        assert config.seed.total_users == 10
        assert config.seed.total_posts_per_user == 5

    def test_total_turns_default(self) -> None:
        assert LocalSimulationConfig.default().total_turns == 3

    def test_feed_defaults(self) -> None:
        config = LocalSimulationConfig.default()

        assert config.feed.algorithm == "most_liked"
        assert config.feed.max_posts == 25
        assert config.feed.include_probability == 0.5

    def test_action_defaults(self) -> None:
        config = LocalSimulationConfig.default()

        assert config.action.max_likes_per_turn == 10
        assert config.action.max_posts_per_turn == 5
        assert config.action.max_follows_per_turn == 5
        assert config.action.max_comments_per_turn == 5

    def test_llm_defaults(self) -> None:
        config = LocalSimulationConfig.default()

        assert config.llm.model == "gpt-5-nano"
        assert config.llm.temperature == 0.7

    def test_storage_default_db_path(self) -> None:
        config = LocalSimulationConfig.default()

        assert str(config.storage.db_path) == "simulation_v2/local_simulation.sqlite3"


class TestLocalSimulationConfigValidation:
    @pytest.mark.parametrize(
        ("field_path", "invalid_value"),
        [
            ("seed.total_users", 0),
            ("seed.total_posts_per_user", 0),
            ("total_turns", 0),
            ("feed.include_probability", -0.1),
            ("feed.include_probability", 1.1),
            ("action.max_likes_per_turn", -1),
            ("action.max_posts_per_turn", -1),
            ("action.max_follows_per_turn", -1),
            ("action.max_comments_per_turn", -1),
        ],
    )
    def test_rejects_invalid_values(
        self, field_path: str, invalid_value: object
    ) -> None:
        payload = LocalSimulationConfig.default().model_dump()
        parts = field_path.split(".")
        target = payload
        for part in parts[:-1]:
            target = target[part]
        target[parts[-1]] = invalid_value

        with pytest.raises(ValidationError):
            LocalSimulationConfig.model_validate(payload)


class TestLocalSimulationConfigSerialization:
    def test_json_round_trip(self) -> None:
        config = LocalSimulationConfig.default()

        restored = LocalSimulationConfig.model_validate_json(config.model_dump_json())

        assert restored == config
