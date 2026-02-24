"""Shared fixtures and helpers for db.repository tests."""

from contextlib import contextmanager
from unittest.mock import Mock

from db.adapters.base import TransactionProvider


def make_mock_transaction_provider() -> TransactionProvider:
    """Create a mock TransactionProvider that yields a mock conn."""

    class MockTransactionProvider:
        @contextmanager
        def run_transaction(self):
            conn = Mock()
            yield conn

    return MockTransactionProvider()  # type: ignore[return-value]
