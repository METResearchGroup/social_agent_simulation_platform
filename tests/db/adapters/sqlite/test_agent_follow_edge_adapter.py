"""Tests for db.adapters.sqlite.agent_follow_edge_adapter module."""

from unittest.mock import Mock

import pytest

from db.adapters.sqlite.agent_follow_edge_adapter import SQLiteAgentFollowEdgeAdapter
from tests.db.adapters.sqlite.conftest import create_mock_row


@pytest.fixture
def adapter():
    return SQLiteAgentFollowEdgeAdapter()


class TestSQLiteAgentFollowEdgeAdapterReadEdgesForFollowerAgentIds:
    def test_uses_normalized_follower_agent_ids_in_query(
        self, adapter, mock_db_connection
    ):
        row = create_mock_row(
            {
                "agent_follow_edge_id": "edge_1",
                "follower_agent_id": "agent_a",
                "target_agent_id": "agent_b",
                "created_at": "2026-03-17T00:00:00Z",
            }
        )

        with mock_db_connection() as (mock_conn, mock_cursor):
            mock_cursor.fetchall = Mock(return_value=[row])

            result = adapter.read_edges_for_follower_agent_ids(
                [" agent_a ", "agent_b"],
                conn=mock_conn,
            )

        assert [edge.agent_follow_edge_id for edge in result] == ["edge_1"]
        sql, params = mock_conn.execute.call_args[0]
        assert "WHERE follower_agent_id IN (?, ?)" in sql
        assert params == ("agent_a", "agent_b")
