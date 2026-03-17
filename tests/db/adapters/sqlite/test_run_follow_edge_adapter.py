"""Tests for db.adapters.sqlite.run_follow_edge_adapter module."""

import sqlite3

import pytest

from db.adapters.sqlite.run_follow_edge_adapter import SQLiteRunFollowEdgeAdapter
from tests.db.adapters.sqlite.conftest import create_mock_row
from tests.factories import RunFollowEdgeSnapshotFactory


@pytest.fixture
def adapter():
    return SQLiteRunFollowEdgeAdapter()


class TestSQLiteRunFollowEdgeAdapterWriteRunFollowEdges:
    def test_writes_rows_with_insert_sql(self, adapter, mock_db_connection):
        rows = [
            RunFollowEdgeSnapshotFactory.create(
                run_id="run_123",
                follower_agent_id="did:plc:agent1",
                target_agent_id="did:plc:agent2",
            ),
            RunFollowEdgeSnapshotFactory.create(
                run_id="run_123",
                follower_agent_id="did:plc:agent2",
                target_agent_id="did:plc:agent3",
            ),
        ]

        with mock_db_connection() as (mock_conn, _):
            adapter.write_run_follow_edges("run_123", rows, conn=mock_conn)

        mock_conn.executemany.assert_called_once()
        sql, params = mock_conn.executemany.call_args[0]
        assert sql.startswith("INSERT INTO run_follow_edges")
        assert params[0][0] == "run_123"
        assert params[0][1] == "did:plc:agent1"
        assert params[0][2] == "did:plc:agent2"
        assert params[1][1] == "did:plc:agent2"
        assert params[1][2] == "did:plc:agent3"

    def test_raises_when_row_run_id_does_not_match(self, adapter, mock_db_connection):
        row = RunFollowEdgeSnapshotFactory.create(run_id="run_other")

        with mock_db_connection() as (mock_conn, _):
            with pytest.raises(ValueError, match="must match the provided run_id"):
                adapter.write_run_follow_edges("run_123", [row], conn=mock_conn)

        mock_conn.executemany.assert_not_called()

    def test_raises_when_row_is_self_follow(self, adapter, mock_db_connection):
        row = RunFollowEdgeSnapshotFactory.create(
            run_id="run_123",
            follower_agent_id="did:plc:agent1",
            target_agent_id="did:plc:agent1",
        )

        with mock_db_connection() as (mock_conn, _):
            with pytest.raises(ValueError, match="cannot contain self-follow"):
                adapter.write_run_follow_edges("run_123", [row], conn=mock_conn)

        mock_conn.executemany.assert_not_called()


class TestSQLiteRunFollowEdgeAdapterReadRunFollowEdgesForRun:
    def test_returns_snapshots_in_deterministic_order(
        self, adapter, mock_db_connection
    ):
        row_one = create_mock_row(
            {
                "run_id": "run_123",
                "follower_agent_id": "did:plc:agent1",
                "target_agent_id": "did:plc:agent2",
                "created_at": "2026-03-17T00:00:00Z",
            }
        )
        row_two = create_mock_row(
            {
                "run_id": "run_123",
                "follower_agent_id": "did:plc:agent2",
                "target_agent_id": "did:plc:agent3",
                "created_at": "2026-03-17T00:00:00Z",
            }
        )

        with mock_db_connection() as (mock_conn, mock_cursor):
            mock_cursor.fetchall.return_value = [row_one, row_two]

            result = adapter.read_run_follow_edges_for_run("run_123", conn=mock_conn)

        assert [
            (snapshot.follower_agent_id, snapshot.target_agent_id)
            for snapshot in result
        ] == [
            ("did:plc:agent1", "did:plc:agent2"),
            ("did:plc:agent2", "did:plc:agent3"),
        ]
        mock_conn.execute.assert_called_once_with(
            "SELECT * FROM run_follow_edges WHERE run_id = ? "
            "ORDER BY follower_agent_id ASC, target_agent_id ASC",
            ("run_123",),
        )

    def test_raises_when_required_column_is_missing(self, adapter, mock_db_connection):
        row = create_mock_row(
            {
                "run_id": "run_123",
                "follower_agent_id": "did:plc:agent1",
                "target_agent_id": "did:plc:agent2",
            }
        )

        with mock_db_connection() as (mock_conn, mock_cursor):
            mock_cursor.fetchall.return_value = [row]

            with pytest.raises(KeyError):
                adapter.read_run_follow_edges_for_run("run_123", conn=mock_conn)

    def test_propagates_sqlite_errors(self, adapter, mock_db_connection):
        with mock_db_connection() as (mock_conn, _):
            mock_conn.execute.side_effect = sqlite3.OperationalError("locked")

            with pytest.raises(sqlite3.OperationalError, match="locked"):
                adapter.read_run_follow_edges_for_run("run_123", conn=mock_conn)
