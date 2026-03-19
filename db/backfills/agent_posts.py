"""Idempotent backfill/import of agent_posts from canonical feed_posts.

This backfill intentionally limits itself to posts attributable to internal
agents (feed_posts.author_handle matching agent.handle).
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass

from db.adapters.sqlite.agent_adapter import SQLiteAgentAdapter
from db.adapters.sqlite.agent_post_adapter import SQLiteAgentPostAdapter
from db.adapters.sqlite.feed_post_adapter import SQLiteFeedPostAdapter
from db.adapters.sqlite.user_agent_profile_metadata_adapter import (
    SQLiteUserAgentProfileMetadataAdapter,
)
from simulation.core.models.agent_posts import AgentPost


@dataclass(frozen=True)
class BackfillAgentPostsResult:
    feed_posts_total: int
    feed_posts_internal: int
    agent_posts_inserted: int
    internal_agents_total: int


def _deterministic_agent_post_id(*, source: str, source_post_id: str) -> str:
    digest = hashlib.sha256(f"{source}:{source_post_id}".encode()).hexdigest()
    return f"agent_post_import_{digest}"


def backfill_agent_posts_from_feed_posts(
    *,
    conn: sqlite3.Connection,
    now_timestamp: str,
) -> BackfillAgentPostsResult:
    """Backfill agent_posts from feed_posts for internal agents.

    Args:
        conn: SQLite connection with foreign_keys enabled.
        now_timestamp: Timestamp used for created_at/updated_at on inserted rows
            and for metadata sync updated_at.

    Returns:
        BackfillAgentPostsResult with summary counters.
    """
    agent_adapter = SQLiteAgentAdapter()
    feed_post_adapter = SQLiteFeedPostAdapter()
    agent_post_adapter = SQLiteAgentPostAdapter()
    metadata_adapter = SQLiteUserAgentProfileMetadataAdapter()

    agents = agent_adapter.read_all_agents(conn=conn)
    handle_to_agent_id = {agent.handle: agent.agent_id for agent in agents}

    feed_posts = feed_post_adapter.read_all_feed_posts(conn=conn)
    internal_feed_posts = [
        post for post in feed_posts if post.author_handle in handle_to_agent_id
    ]

    before_count = agent_post_adapter.count_all_posts(conn=conn)

    imported_posts: list[AgentPost] = []
    for post in internal_feed_posts:
        agent_id = handle_to_agent_id[post.author_handle]
        source = post.source.value
        source_post_id = post.post_id
        agent_post_id = _deterministic_agent_post_id(
            source=source,
            source_post_id=source_post_id,
        )
        import_metadata_json = json.dumps(
            {
                "bookmark_count": post.bookmark_count,
                "like_count": post.like_count,
                "quote_count": post.quote_count,
                "reply_count": post.reply_count,
                "repost_count": post.repost_count,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        imported_posts.append(
            AgentPost(
                agent_post_id=agent_post_id,
                agent_id=agent_id,
                body_text=post.text,
                published_at=post.created_at,
                created_at=now_timestamp,
                updated_at=now_timestamp,
                source_post_id=source_post_id,
                source=source,
                source_uri=post.uri,
                imported_author_handle=post.author_handle,
                imported_author_display_name=post.author_display_name,
                import_metadata_json=import_metadata_json,
            )
        )

    agent_post_adapter.upsert_imported_agent_posts(imported_posts, conn=conn)

    after_count = agent_post_adapter.count_all_posts(conn=conn)
    inserted_count = after_count - before_count
    if inserted_count < 0:
        raise RuntimeError(
            "agent_posts row count decreased during backfill; expected monotonic increase"
        )

    agent_ids = [agent.agent_id for agent in agents]
    posts_by_agent_id = agent_post_adapter.count_posts_by_agent_ids(
        agent_ids, conn=conn
    )
    for agent_id, count in posts_by_agent_id.items():
        metadata_adapter.sync_posts_count(
            agent_id=agent_id,
            posts_count=count,
            updated_at=now_timestamp,
            conn=conn,
        )

    return BackfillAgentPostsResult(
        feed_posts_total=len(feed_posts),
        feed_posts_internal=len(internal_feed_posts),
        agent_posts_inserted=inserted_count,
        internal_agents_total=len(agents),
    )
