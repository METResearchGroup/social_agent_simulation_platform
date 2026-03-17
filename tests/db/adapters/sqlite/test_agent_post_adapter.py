"""Tests for db.adapters.sqlite.agent_post_adapter module."""

import sqlite3

import pytest

from db.adapters.sqlite.agent_post_adapter import SQLiteAgentPostAdapter
from simulation.core.models.agent_posts import AgentPost
from tests.db.adapters.sqlite.conftest import create_mock_row


@pytest.fixture
def adapter():
    return SQLiteAgentPostAdapter()


class TestSQLiteAgentPostAdapterUpsertImportedAgentPosts:
    def test_raises_when_source_post_id_missing(self, adapter, mock_db_connection):
        post = AgentPost(
            agent_post_id="agent_post_1",
            agent_id="did:plc:agent1",
            body_text="hello",
            published_at="2026-03-17T00:00:00Z",
            created_at="2026-03-17T00:00:00Z",
            updated_at="2026-03-17T00:00:00Z",
            source_post_id=None,
            source="bluesky",
        )

        with mock_db_connection() as (mock_conn, _):
            with pytest.raises(ValueError, match="must provide source_post_id"):
                adapter.upsert_imported_agent_posts([post], conn=mock_conn)

        mock_conn.executemany.assert_not_called()

    def test_raises_when_source_missing(self, adapter, mock_db_connection):
        post = AgentPost(
            agent_post_id="agent_post_1",
            agent_id="did:plc:agent1",
            body_text="hello",
            published_at="2026-03-17T00:00:00Z",
            created_at="2026-03-17T00:00:00Z",
            updated_at="2026-03-17T00:00:00Z",
            source_post_id="bluesky:at://post/1",
            source=None,
        )

        with mock_db_connection() as (mock_conn, _):
            with pytest.raises(ValueError, match="must provide source"):
                adapter.upsert_imported_agent_posts([post], conn=mock_conn)

        mock_conn.executemany.assert_not_called()

    def test_uses_on_conflict_upsert_sql(self, adapter, mock_db_connection):
        post = AgentPost(
            agent_post_id="agent_post_1",
            agent_id="did:plc:agent1",
            body_text="hello",
            published_at="2026-03-17T00:00:00Z",
            created_at="2026-03-17T01:00:00Z",
            updated_at="2026-03-17T01:00:00Z",
            source_post_id="bluesky:at://post/1",
            source="bluesky",
        )

        with mock_db_connection() as (mock_conn, _):
            adapter.upsert_imported_agent_posts([post], conn=mock_conn)

        mock_conn.executemany.assert_called_once()
        sql, params = mock_conn.executemany.call_args[0]
        assert sql.startswith("INSERT INTO agent_posts")
        assert "ON CONFLICT(source, source_post_id) DO UPDATE SET" in sql
        assert "WHERE agent_posts." in sql
        assert params[0][0] == "agent_post_1"


class TestSQLiteAgentPostAdapterReadPostsForAgentIds:
    def test_returns_posts_in_deterministic_order(self, adapter, mock_db_connection):
        row_one = create_mock_row(
            {
                "agent_post_id": "agent_post_1",
                "agent_id": "did:plc:agent1",
                "body_text": "one",
                "published_at": "2026-03-17T00:00:00Z",
                "created_at": "2026-03-17T01:00:00Z",
                "updated_at": "2026-03-17T01:00:00Z",
                "source_post_id": "bluesky:at://post/1",
                "source": "bluesky",
                "source_uri": "at://post/1",
                "imported_author_handle": "agent1.bsky.social",
                "imported_author_display_name": "Agent 1",
                "import_metadata_json": "{}",
            }
        )
        row_two = create_mock_row(
            {
                "agent_post_id": "agent_post_2",
                "agent_id": "did:plc:agent2",
                "body_text": "two",
                "published_at": "2026-03-17T00:00:00Z",
                "created_at": "2026-03-17T01:00:00Z",
                "updated_at": "2026-03-17T01:00:00Z",
                "source_post_id": "bluesky:at://post/2",
                "source": "bluesky",
                "source_uri": "at://post/2",
                "imported_author_handle": "agent2.bsky.social",
                "imported_author_display_name": "Agent 2",
                "import_metadata_json": "{}",
            }
        )

        with mock_db_connection() as (mock_conn, mock_cursor):
            mock_cursor.fetchall.return_value = [row_one, row_two]

            result = adapter.read_posts_for_agent_ids(
                ["did:plc:agent1", "did:plc:agent2"], conn=mock_conn
            )

        assert [post.agent_post_id for post in result] == [
            "agent_post_1",
            "agent_post_2",
        ]
        sql, params = mock_conn.execute.call_args[0]
        assert "FROM agent_posts" in sql
        assert "ORDER BY agent_id ASC, published_at ASC, agent_post_id ASC" in sql
        assert params == ("did:plc:agent1", "did:plc:agent2")

    def test_propagates_sqlite_errors(self, adapter, mock_db_connection):
        with mock_db_connection() as (mock_conn, _):
            mock_conn.execute.side_effect = sqlite3.OperationalError("locked")

            with pytest.raises(sqlite3.OperationalError, match="locked"):
                adapter.read_posts_for_agent_ids(["did:plc:agent1"], conn=mock_conn)
