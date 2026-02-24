"""Tests for db.adapters.sqlite.metrics_adapter module."""

from unittest.mock import Mock

import pytest

from db.adapters.sqlite.metrics_adapter import SQLiteMetricsAdapter
from simulation.core.models.metrics import RunMetrics, TurnMetrics


@pytest.fixture
def adapter():
    """Create a SQLiteMetricsAdapter instance."""
    return SQLiteMetricsAdapter()


def test_write_run_metrics_raises_value_error_when_conn_is_none(adapter):
    """When conn is None, write_run_metrics raises ValueError."""
    run_metrics = RunMetrics(
        run_id="run_1",
        metrics={"run.actions.total": 10},
        created_at="2026-01-01T00:00:00",
    )
    with pytest.raises(ValueError, match="conn is required"):
        adapter.write_run_metrics(run_metrics, conn=None)


def test_write_run_metrics_with_conn_does_not_commit(adapter):
    """When conn is passed, write_run_metrics uses it and does not call commit."""
    run_metrics = RunMetrics(
        run_id="run_1",
        metrics={"run.actions.total": 10},
        created_at="2026-01-01T00:00:00",
    )
    mock_conn = Mock()
    adapter.write_run_metrics(run_metrics, conn=mock_conn)
    mock_conn.execute.assert_called_once()
    mock_conn.commit.assert_not_called()


def test_write_turn_metrics_raises_value_error_when_conn_is_none(adapter):
    """When conn is None, write_turn_metrics raises ValueError."""
    turn_metrics = TurnMetrics(
        run_id="run_1",
        turn_number=0,
        metrics={"turn.actions.total": 1},
        created_at="2026-01-01T00:00:00",
    )
    with pytest.raises(ValueError, match="conn is required"):
        adapter.write_turn_metrics(turn_metrics, conn=None)
