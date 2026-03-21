"""Shared pytest fixtures and utilities for SQLite adapter tests."""

from contextlib import contextmanager
from unittest.mock import MagicMock, Mock

import pytest

from lib.agent_id import canonical_agent_id


def create_mock_row(row_data: dict) -> MagicMock:
    """Helper function to create a mock sqlite3.Row.

    Args:
        row_data: Dictionary mapping column names to values

    Returns:
        MagicMock configured to behave like a sqlite3.Row
    """
    row_data = dict(row_data)
    if "uri" in row_data and "post_id" not in row_data and row_data["uri"] is not None:
        row_data["post_id"] = f"bluesky:{row_data['uri']}"
    if "uri" in row_data and "source" not in row_data:
        row_data["source"] = "bluesky"
    if "author_handle" in row_data and "author_agent_id" not in row_data:
        row_data["author_agent_id"] = canonical_agent_id(row_data["author_handle"])
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
