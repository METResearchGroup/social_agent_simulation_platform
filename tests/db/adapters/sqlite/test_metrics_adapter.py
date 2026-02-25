"""Tests for db.adapters.sqlite.metrics_adapter module."""

from unittest.mock import Mock

import pytest

from db.adapters.sqlite.metrics_adapter import SQLiteMetricsAdapter
from tests.factories import RunMetricsFactory


@pytest.fixture
def adapter():
    """Create a SQLiteMetricsAdapter instance."""
    return SQLiteMetricsAdapter()


def test_write_run_metrics_with_conn_does_not_commit(adapter):
    """When conn is passed, write_run_metrics uses it and does not call commit."""
    run_metrics = RunMetricsFactory.create(
        run_id="run_1",
        metrics={"run.actions.total": 10},
        created_at="2026-01-01T00:00:00",
    )
    mock_conn = Mock()
    adapter.write_run_metrics(run_metrics, conn=mock_conn)
    mock_conn.execute.assert_called_once()
    mock_conn.commit.assert_not_called()
