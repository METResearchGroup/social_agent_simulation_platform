"""Shared pytest fixtures and utilities for SQLite adapter tests."""

from contextlib import contextmanager
from unittest.mock import MagicMock, Mock

import pytest


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


def create_mock_conn_context():
    """Create a context manager yielding (mock_conn, mock_cursor) for adapter tests.

    Adapters receive conn from the repository (via run_transaction); they no longer
    call get_connection. Tests pass conn=mock_conn to adapter methods directly.
    """

    @contextmanager
    def _mock_conn_context():
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.execute.return_value = mock_cursor
        yield mock_conn, mock_cursor

    return _mock_conn_context


@pytest.fixture
def mock_db_connection(request: pytest.FixtureRequest):
    """Return a context-manager factory yielding (mock_conn, mock_cursor).

    Adapters no longer call get_connection; they receive conn as a parameter.
    Tests should pass conn=mock_conn to adapter methods.
    """
    return create_mock_conn_context()
