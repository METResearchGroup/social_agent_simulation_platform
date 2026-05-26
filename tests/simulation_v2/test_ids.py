"""Tests for simulation_v2 UUID identifier helpers."""

from __future__ import annotations

import uuid

import pytest

from simulation_v2 import ids

ID_HELPERS = [
    ids.new_run_id,
    ids.new_turn_id,
    ids.new_action_id,
    ids.new_feed_id,
    ids.new_generation_id,
    ids.new_memory_diff_id,
]


class TestIdHelpers:
    @pytest.mark.parametrize("helper", ID_HELPERS)
    def test_returns_non_empty_uuid4_string(self, helper) -> None:
        value = helper()

        assert isinstance(value, str)
        assert value
        parsed = uuid.UUID(value)
        assert parsed.version == 4

    @pytest.mark.parametrize("helper", ID_HELPERS)
    def test_consecutive_calls_differ(self, helper) -> None:
        first = helper()
        second = helper()

        assert first != second
