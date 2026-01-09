"""Shared pytest fixtures and utilities for SQLite adapter tests."""

from contextlib import contextmanager
from unittest.mock import MagicMock, Mock, patch


def create_mock_row(row_data: dict) -> MagicMock:
    """Helper function to create a mock sqlite3.Row.

    Args:
        row_data: Dictionary mapping column names to values

    Returns:
        MagicMock configured to behave like a sqlite3.Row
    """
    mock_row = MagicMock()
    mock_row.__getitem__ = Mock(side_effect=lambda key: row_data[key])
    mock_row.keys = Mock(return_value=list(row_data.keys()))
    return mock_row


def create_mock_db_connection(patch_target: str):
    """Factory function to create a reusable mock database connection context manager.

    Args:
        patch_target: The import path to patch for get_connection (e.g.,
            "db.adapters.sqlite.profile_adapter.get_connection")

    Returns:
        A context manager that yields (mock_get_conn, mock_conn, mock_cursor)
    """

    @contextmanager
    def _mock_db_connection():
        # Patch where it's used, not where it's defined
        with patch(patch_target) as mock_get_conn:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.__enter__ = Mock(return_value=mock_conn)
            mock_conn.__exit__ = Mock(return_value=None)
            mock_conn.execute.return_value = mock_cursor
            mock_get_conn.return_value = mock_conn
            yield mock_get_conn, mock_conn, mock_cursor

    return _mock_db_connection
