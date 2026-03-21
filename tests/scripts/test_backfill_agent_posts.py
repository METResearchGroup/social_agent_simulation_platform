"""Tests for db.backfills.agent_posts backfill behavior."""

import sqlite3

from db.backfills.agent_posts import backfill_agent_posts_from_feed_posts
from tests.factories import AgentRecordFactory, PostFactory


class TestBackfillAgentPostsFromFeedPosts:
    def test_backfill_is_idempotent_and_syncs_posts_count(
        self,
        temp_db,
        agent_repo,
        feed_post_repo,
        user_agent_profile_metadata_repo,
    ) -> None:
        agent_repo.create_or_update_agent(
            AgentRecordFactory.create(
                agent_id="did:plc:agent1",
                handle="agent1.bsky.social",
                display_name="Agent 1",
                created_at="2026-03-17T00:00:00Z",
                updated_at="2026-03-17T00:00:00Z",
            )
        )

        feed_post_repo.create_or_update_feed_posts(
            [
                PostFactory.create(
                    uri="at://did:plc:agent1/app.bsky.feed.post/1",
                    author_handle="agent1.bsky.social",
                    author_agent_id="did:plc:agent1",
                    author_display_name="Agent 1",
                    text="hello",
                    created_at="2026-03-17T00:00:00Z",
                ),
            ]
        )

        with sqlite3.connect(temp_db) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("BEGIN")
            result1 = backfill_agent_posts_from_feed_posts(
                conn=conn, now_timestamp="2026-03-17T01:00:00Z"
            )
            conn.execute("COMMIT")

        assert result1.feed_posts_total == 1
        assert result1.feed_posts_internal == 1
        assert result1.agent_posts_inserted == 1

        md1 = user_agent_profile_metadata_repo.get_by_agent_id("did:plc:agent1")
        assert md1 is not None
        assert md1.posts_count == 1
        assert md1.updated_at == "2026-03-17T01:00:00Z"

        with sqlite3.connect(temp_db) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            row = conn.execute("SELECT updated_at FROM agent_posts").fetchone()
            assert row is not None
            updated_at_before = str(row["updated_at"])

        with sqlite3.connect(temp_db) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("BEGIN")
            result2 = backfill_agent_posts_from_feed_posts(
                conn=conn, now_timestamp="2026-03-17T02:00:00Z"
            )
            conn.execute("COMMIT")

        assert result2.agent_posts_inserted == 0
        md2 = user_agent_profile_metadata_repo.get_by_agent_id("did:plc:agent1")
        assert md2 is not None
        assert md2.posts_count == 1
        assert md2.updated_at == "2026-03-17T01:00:00Z"

        with sqlite3.connect(temp_db) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            row = conn.execute("SELECT updated_at FROM agent_posts").fetchone()
            assert row is not None
            updated_at_after = str(row["updated_at"])

        assert updated_at_after == updated_at_before
