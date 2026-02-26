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


class TestMetricsAdapterEdgeCases:
    """Additional edge case tests for SQLiteMetricsAdapter."""

    def test_write_run_metrics_with_empty_metrics_dict(self, adapter):
        """Test that write_run_metrics handles empty metrics dictionary."""
        # Arrange
        run_metrics = RunMetricsFactory.create(
            run_id="run_empty",
            metrics={},
            created_at="2026-01-01T00:00:00",
        )
        mock_conn = Mock()

        # Act
        adapter.write_run_metrics(run_metrics, conn=mock_conn)

        # Assert
        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args
        assert "INSERT OR REPLACE INTO run_metrics" in call_args[0][0]

    def test_write_run_metrics_with_nested_metrics(self, adapter):
        """Test that write_run_metrics handles nested metrics structure."""
        # Arrange
        run_metrics = RunMetricsFactory.create(
            run_id="run_nested",
            metrics={
                "category1": {"subcategory1": 10, "subcategory2": 20},
                "category2": {"value": 30},
            },
            created_at="2026-01-01T00:00:00",
        )
        mock_conn = Mock()

        # Act
        adapter.write_run_metrics(run_metrics, conn=mock_conn)

        # Assert
        mock_conn.execute.assert_called_once()

    def test_write_run_metrics_with_large_metrics_dict(self, adapter):
        """Test that write_run_metrics handles large metrics dictionary."""
        # Arrange
        large_metrics = {f"metric_{i}": i for i in range(1000)}
        run_metrics = RunMetricsFactory.create(
            run_id="run_large",
            metrics=large_metrics,
            created_at="2026-01-01T00:00:00",
        )
        mock_conn = Mock()

        # Act
        adapter.write_run_metrics(run_metrics, conn=mock_conn)

        # Assert
        mock_conn.execute.assert_called_once()

    def test_write_run_metrics_with_special_characters_in_keys(self, adapter):
        """Test that write_run_metrics handles special characters in metric keys."""
        # Arrange
        run_metrics = RunMetricsFactory.create(
            run_id="run_special",
            metrics={
                "metric.with.dots": 10,
                "metric-with-dashes": 20,
                "metric_with_underscores": 30,
                "metric:with:colons": 40,
            },
            created_at="2026-01-01T00:00:00",
        )
        mock_conn = Mock()

        # Act
        adapter.write_run_metrics(run_metrics, conn=mock_conn)

        # Assert
        mock_conn.execute.assert_called_once()

    def test_write_run_metrics_with_various_value_types(self, adapter):
        """Test that write_run_metrics handles various value types in metrics."""
        # Arrange
        run_metrics = RunMetricsFactory.create(
            run_id="run_types",
            metrics={
                "int_value": 42,
                "float_value": 3.14,
                "string_value": "text",
                "bool_value": True,
                "null_value": None,
                "list_value": [1, 2, 3],
            },
            created_at="2026-01-01T00:00:00",
        )
        mock_conn = Mock()

        # Act
        adapter.write_run_metrics(run_metrics, conn=mock_conn)

        # Assert
        mock_conn.execute.assert_called_once()

    def test_read_run_metrics_validates_required_columns(self, adapter):
        """Test that read_run_metrics validates required columns are present."""
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.execute.return_value = mock_cursor

        # Create row missing required column
        mock_row = Mock()
        mock_row.keys.return_value = ["run_id", "created_at"]  # Missing "metrics"
        mock_row.__getitem__ = Mock(side_effect=lambda k: {"run_id": "run_1", "created_at": "2026-01-01T00:00:00"}.get(k))
        mock_cursor.fetchone.return_value = mock_row

        # Act & Assert
        with pytest.raises(KeyError, match="metrics"):
            adapter.read_run_metrics("run_1", conn=mock_conn)

    def test_read_run_metrics_validates_no_null_values(self, adapter):
        """Test that read_run_metrics validates required columns are not NULL."""
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.execute.return_value = mock_cursor

        # Create row with NULL metrics
        mock_row = Mock()
        mock_row.keys.return_value = ["run_id", "metrics", "created_at"]
        mock_row.__getitem__ = Mock(
            side_effect=lambda k: {
                "run_id": "run_1",
                "metrics": None,  # NULL value
                "created_at": "2026-01-01T00:00:00",
            }.get(k)
        )
        mock_cursor.fetchone.return_value = mock_row

        # Act & Assert
        with pytest.raises(ValueError, match="NULL"):
            adapter.read_run_metrics("run_1", conn=mock_conn)

    def test_read_run_metrics_handles_invalid_json(self, adapter):
        """Test that read_run_metrics raises error for invalid JSON in metrics."""
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.execute.return_value = mock_cursor

        # Create row with invalid JSON
        mock_row = Mock()
        mock_row.keys.return_value = ["run_id", "metrics", "created_at"]
        mock_row.__getitem__ = Mock(
            side_effect=lambda k: {
                "run_id": "run_1",
                "metrics": "{invalid json}",  # Invalid JSON
                "created_at": "2026-01-01T00:00:00",
            }.get(k)
        )
        mock_cursor.fetchone.return_value = mock_row

        # Act & Assert
        with pytest.raises(ValueError, match="Could not parse metrics as JSON"):
            adapter.read_run_metrics("run_1", conn=mock_conn)

    def test_read_run_metrics_rejects_non_dict_metrics(self, adapter):
        """Test that read_run_metrics rejects metrics that are not a dictionary."""
        # Arrange
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.execute.return_value = mock_cursor

        # Create row with non-dict metrics (array)
        mock_row = Mock()
        mock_row.keys.return_value = ["run_id", "metrics", "created_at"]
        mock_row.__getitem__ = Mock(
            side_effect=lambda k: {
                "run_id": "run_1",
                "metrics": "[1, 2, 3]",  # Array instead of object
                "created_at": "2026-01-01T00:00:00",
            }.get(k)
        )
        mock_cursor.fetchone.return_value = mock_row

        # Act & Assert
        with pytest.raises(ValueError, match="metrics must be a JSON object"):
            adapter.read_run_metrics("run_1", conn=mock_conn)