"""Shared fixtures and helpers for db.repository tests."""

from contextlib import contextmanager
from unittest.mock import Mock

import pytest

from db.adapters.base import TransactionProvider
from db.adapters.sqlite.sqlite import get_connection
from simulation.core.models.agent import Agent, PersonaSource


def ensure_run_exists(run_id: str) -> None:
    """Ensure a matching `runs` row exists for FK enforcement (e.g. generated_feed tests)."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO runs
            (run_id, created_at, total_turns, total_agents, started_at, status, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                "2024-01-01T00:00:00Z",
                1,
                1,
                "2024-01-01T00:00:00Z",
                "running",
                None,
            ),
        )
        conn.commit()


@pytest.fixture
def agent_in_db(agent_repo):
    """Create an agent in the database for bio tests (test.bsky.social)."""
    agent = Agent(
        agent_id="did:plc:test123",
        handle="test.bsky.social",
        persona_source=PersonaSource.SYNC_BLUESKY,
        display_name="Test User",
        created_at="2026_02_19-10:00:00",
        updated_at="2026_02_19-10:00:00",
    )
    agent_repo.create_or_update_agent(agent)
    return "did:plc:test123"


@pytest.fixture
def agent_in_db_meta(agent_repo):
    """Create an agent in the database for metadata tests (meta.bsky.social)."""
    agent = Agent(
        agent_id="did:plc:meta123",
        handle="meta.bsky.social",
        persona_source=PersonaSource.SYNC_BLUESKY,
        display_name="Meta User",
        created_at="2026_02_19-10:00:00",
        updated_at="2026_02_19-10:00:00",
    )
    agent_repo.create_or_update_agent(agent)
    return "did:plc:meta123"


def make_mock_transaction_provider() -> TransactionProvider:
    """Create a mock TransactionProvider that yields a mock conn."""

    class MockTransactionProvider:
        @contextmanager
        def run_transaction(self):
            conn = Mock()
            yield conn

    return MockTransactionProvider()  # type: ignore[return-value]
