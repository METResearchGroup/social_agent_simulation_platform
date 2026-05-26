"""Tests for simulation_v2 progress helpers."""

from __future__ import annotations

import logging

from simulation_v2.lib.decorators import (
    iteration_log_level,
    no_progress,
    progress_enabled,
    progress_items,
)


def test_progress_enabled_by_default() -> None:
    assert progress_enabled() is True


def test_no_progress_disables_bars_and_uses_info_log_level() -> None:
    with no_progress():
        assert progress_enabled() is False
        assert iteration_log_level() == logging.INFO
        assert list(progress_items([1, 2, 3], desc="test")) == [1, 2, 3]


def test_progress_items_yields_all_items_when_disabled() -> None:
    with no_progress():
        assert list(progress_items(range(5), desc="test", unit="x")) == list(range(5))
