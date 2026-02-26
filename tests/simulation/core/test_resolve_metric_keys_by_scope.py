"""Tests for resolve_metric_keys_by_scope."""

import pytest

from simulation.core.metrics.defaults import (
    REGISTERED_METRIC_KEYS,
    resolve_metric_keys_by_scope,
)


def test_resolve_metric_keys_by_scope_splits_correctly():
    """Split metric keys into turn and run lists by scope."""
    metric_keys = [
        "turn.actions.total",
        "run.actions.total",
        "turn.actions.counts_by_type",
        "run.actions.total_by_type",
    ]
    turn_keys, run_keys = resolve_metric_keys_by_scope(metric_keys)

    assert turn_keys == ["turn.actions.counts_by_type", "turn.actions.total"]
    assert run_keys == ["run.actions.total", "run.actions.total_by_type"]


def test_resolve_metric_keys_by_scope_turn_only():
    """Only turn keys returns empty run list."""
    metric_keys = ["turn.actions.counts_by_type", "turn.actions.total"]
    turn_keys, run_keys = resolve_metric_keys_by_scope(metric_keys)

    assert turn_keys == ["turn.actions.counts_by_type", "turn.actions.total"]
    assert run_keys == []


def test_resolve_metric_keys_by_scope_run_only():
    """Only run keys returns empty turn list."""
    metric_keys = ["run.actions.total_by_type", "run.actions.total"]
    turn_keys, run_keys = resolve_metric_keys_by_scope(metric_keys)

    assert turn_keys == []
    assert run_keys == ["run.actions.total", "run.actions.total_by_type"]


def test_resolve_metric_keys_by_scope_duplicate_keys_raises():
    """Duplicate metric keys raise ValueError before scope validation."""
    metric_keys = [
        "turn.actions.total",
        "run.actions.total",
        "turn.actions.total",
    ]

    with pytest.raises(ValueError) as exc_info:
        resolve_metric_keys_by_scope(metric_keys)

    msg = str(exc_info.value)
    assert "duplicate keys" in msg.lower()
    assert "turn.actions.total" in msg


def test_resolve_metric_keys_by_scope_unknown_key_raises():
    """Unknown metric key raises ValueError."""
    metric_keys = ["turn.actions.counts_by_type", "unknown.metric.key"]

    with pytest.raises(ValueError) as exc_info:
        resolve_metric_keys_by_scope(metric_keys)

    assert "unknown.metric.key" in str(exc_info.value)
    assert "registered keys" in str(exc_info.value).lower()


def test_registered_metric_keys_contains_all_builtins():
    """REGISTERED_METRIC_KEYS contains all four built-in metrics."""
    expected = {
        "turn.actions.counts_by_type",
        "turn.actions.total",
        "run.actions.total_by_type",
        "run.actions.total",
    }
    assert expected == REGISTERED_METRIC_KEYS
