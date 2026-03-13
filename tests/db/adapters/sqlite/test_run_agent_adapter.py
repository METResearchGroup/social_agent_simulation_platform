"""Tests for db.adapters.sqlite.run_agent_adapter module."""

import sqlite3
from unittest.mock import Mock

import pytest

from db.adapters.sqlite.run_agent_adapter import SQLiteRunAgentAdapter
from tests.db.adapters.sqlite.conftest import create_mock_row
from tests.factories import RunAgentSnapshotFactory


@pytest.fixture
def adapter():
    return SQLiteRunAgentAdapter()


class TestSQLiteRunAgentAdapterWriteRunAgents:
    def test_writes_rows_with_insert_sql(self, adapter, mock_db_connection):
        rows = [
            RunAgentSnapshotFactory.create(
                run_id="run_123",
                agent_id="did:plc:agent1",
                selection_order=0,
                handle_at_start="agent1.bsky.social",
            ),
            RunAgentSnapshotFactory.create(
                run_id="run_123",
                agent_id="did:plc:agent2",
                selection_order=1,
                handle_at_start="agent2.bsky.social",
            ),
        ]

        with mock_db_connection() as (mock_conn, _):
            adapter.write_run_agents("run_123", rows, conn=mock_conn)

        mock_conn.executemany.assert_called_once()
        sql, params = mock_conn.executemany.call_args[0]
        assert sql.startswith("INSERT INTO run_agents")
        assert params[0][0] == "run_123"
        assert params[0][1] == "did:plc:agent1"
        assert params[0][2] == 0
        assert params[1][1] == "did:plc:agent2"
        assert params[1][2] == 1

    def test_raises_when_row_run_id_does_not_match(self, adapter, mock_db_connection):
        row = RunAgentSnapshotFactory.create(run_id="run_other")

        with mock_db_connection() as (mock_conn, _):
            with pytest.raises(ValueError, match="must match the provided run_id"):
                adapter.write_run_agents("run_123", [row], conn=mock_conn)

        mock_conn.executemany.assert_not_called()


class TestSQLiteRunAgentAdapterReadRunAgentsForRun:
    def test_returns_snapshots_in_selection_order(self, adapter, mock_db_connection):
        row_one = create_mock_row(
            {
                "run_id": "run_123",
                "agent_id": "did:plc:agent1",
                "selection_order": 0,
                "handle_at_start": "agent1.bsky.social",
                "display_name_at_start": "Agent One",
                "persona_bio_at_start": "Bio one",
                "followers_count_at_start": 10,
                "follows_count_at_start": 11,
                "posts_count_at_start": 12,
                "created_at": "2026-03-13T00:00:00Z",
            }
        )
        row_two = create_mock_row(
            {
                "run_id": "run_123",
                "agent_id": "did:plc:agent2",
                "selection_order": 1,
                "handle_at_start": "agent2.bsky.social",
                "display_name_at_start": "Agent Two",
                "persona_bio_at_start": "Bio two",
                "followers_count_at_start": 20,
                "follows_count_at_start": 21,
                "posts_count_at_start": 22,
                "created_at": "2026-03-13T00:00:00Z",
            }
        )

        with mock_db_connection() as (mock_conn, mock_cursor):
            mock_cursor.fetchall = Mock(return_value=[row_one, row_two])

            result = adapter.read_run_agents_for_run("run_123", conn=mock_conn)

        assert [snapshot.selection_order for snapshot in result] == [0, 1]
        assert [snapshot.agent_id for snapshot in result] == [
            "did:plc:agent1",
            "did:plc:agent2",
        ]
        mock_conn.execute.assert_called_once_with(
            "SELECT * FROM run_agents WHERE run_id = ? ORDER BY selection_order ASC",
            ("run_123",),
        )

    def test_raises_when_required_column_is_missing(self, adapter, mock_db_connection):
        row = create_mock_row(
            {
                "run_id": "run_123",
                "agent_id": "did:plc:agent1",
                "selection_order": 0,
                "handle_at_start": "agent1.bsky.social",
                "display_name_at_start": "Agent One",
                "persona_bio_at_start": "Bio one",
                "followers_count_at_start": 10,
                "follows_count_at_start": 11,
                # posts_count_at_start missing
                "created_at": "2026-03-13T00:00:00Z",
            }
        )

        with mock_db_connection() as (mock_conn, mock_cursor):
            mock_cursor.fetchall = Mock(return_value=[row])

            with pytest.raises(KeyError):
                adapter.read_run_agents_for_run("run_123", conn=mock_conn)

    def test_propagates_sqlite_errors(self, adapter, mock_db_connection):
        with mock_db_connection() as (mock_conn, _):
            mock_conn.execute.side_effect = sqlite3.OperationalError("locked")

            with pytest.raises(sqlite3.OperationalError, match="locked"):
                adapter.read_run_agents_for_run("run_123", conn=mock_conn)
