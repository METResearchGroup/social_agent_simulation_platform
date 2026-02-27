"""Refactor Bluesky feed posts into generic feed_posts and use post_ids everywhere.

Revision ID: e1f0d1c2b3a4
Revises: c3a1d2e4f5a6
Create Date: 2026-02-27 00:00:00.000000
"""

from __future__ import annotations

import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e1f0d1c2b3a4"
down_revision: Union[str, Sequence[str], None] = "c3a1d2e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _prefix_bluesky(post_id_or_uri: str) -> str:
    if post_id_or_uri.startswith("bluesky:"):
        return post_id_or_uri
    return f"bluesky:{post_id_or_uri}"


def _strip_bluesky_prefix(post_id: str) -> str:
    if post_id.startswith("bluesky:"):
        return post_id.split(":", 1)[1]
    return post_id


def upgrade() -> None:
    """Create feed_posts, migrate data, and rename post_uris->post_ids."""
    conn = op.get_bind()

    op.create_table(
        "feed_posts",
        sa.Column("post_id", sa.Text(), primary_key=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("uri", sa.Text(), nullable=False),
        sa.Column("author_display_name", sa.Text(), nullable=False),
        sa.Column("author_handle", sa.Text(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("bookmark_count", sa.Integer(), nullable=False),
        sa.Column("like_count", sa.Integer(), nullable=False),
        sa.Column("quote_count", sa.Integer(), nullable=False),
        sa.Column("reply_count", sa.Integer(), nullable=False),
        sa.Column("repost_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
    )
    op.create_index(
        "idx_feed_posts_author_handle",
        "feed_posts",
        ["author_handle"],
        unique=False,
    )

    # Migrate legacy Bluesky rows.
    conn.execute(
        sa.text(
            """
            INSERT INTO feed_posts (
                post_id,
                source,
                uri,
                author_display_name,
                author_handle,
                text,
                bookmark_count,
                like_count,
                quote_count,
                reply_count,
                repost_count,
                created_at
            )
            SELECT
                'bluesky:' || uri,
                'bluesky',
                uri,
                author_display_name,
                author_handle,
                text,
                bookmark_count,
                like_count,
                quote_count,
                reply_count,
                repost_count,
                created_at
            FROM bluesky_feed_posts
            """
        )
    )

    # Drop old index/table (batch mode not needed for a simple drop).
    op.drop_table("bluesky_feed_posts")

    # Rename generated_feeds.post_uris -> post_ids and prefix existing values.
    with op.batch_alter_table("generated_feeds", schema=None) as batch_op:
        batch_op.alter_column("post_uris", new_column_name="post_ids")

    rows = conn.execute(
        sa.text(
            "SELECT agent_handle, run_id, turn_number, post_ids FROM generated_feeds"
        )
    ).fetchall()
    for row in rows:
        mapping = row._mapping
        raw = mapping["post_ids"]
        try:
            items = json.loads(raw) if raw is not None else []
        except json.JSONDecodeError:
            # Leave invalid JSON as-is; existing adapter/tests already surface this.
            continue
        if not isinstance(items, list):
            continue
        new_items = [_prefix_bluesky(str(item)) for item in items]
        if new_items == items:
            continue
        conn.execute(
            sa.text(
                """
                UPDATE generated_feeds
                SET post_ids = :post_ids
                WHERE agent_handle = :agent_handle AND run_id = :run_id AND turn_number = :turn_number
                """
            ),
            {
                "post_ids": json.dumps(new_items),
                "agent_handle": mapping["agent_handle"],
                "run_id": mapping["run_id"],
                "turn_number": mapping["turn_number"],
            },
        )

    # Prefix persisted action targets (likes/comments) to use canonical post_id.
    conn.execute(
        sa.text(
            "UPDATE likes SET post_id = 'bluesky:' || post_id WHERE post_id NOT LIKE 'bluesky:%'"
        )
    )
    conn.execute(
        sa.text(
            "UPDATE comments SET post_id = 'bluesky:' || post_id WHERE post_id NOT LIKE 'bluesky:%'"
        )
    )


def downgrade() -> None:
    """Reverse feed_posts back to bluesky_feed_posts and post_ids back to post_uris."""
    conn = op.get_bind()

    op.create_table(
        "bluesky_feed_posts",
        sa.Column("uri", sa.Text(), primary_key=True),
        sa.Column("author_display_name", sa.Text(), nullable=False),
        sa.Column("author_handle", sa.Text(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("bookmark_count", sa.Integer(), nullable=False),
        sa.Column("like_count", sa.Integer(), nullable=False),
        sa.Column("quote_count", sa.Integer(), nullable=False),
        sa.Column("reply_count", sa.Integer(), nullable=False),
        sa.Column("repost_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
    )
    op.create_index(
        "idx_bluesky_feed_posts_author_handle",
        "bluesky_feed_posts",
        ["author_handle"],
        unique=False,
    )

    # Restore legacy rows (best-effort: only source='bluesky').
    conn.execute(
        sa.text(
            """
            INSERT INTO bluesky_feed_posts (
                uri,
                author_display_name,
                author_handle,
                text,
                bookmark_count,
                like_count,
                quote_count,
                reply_count,
                repost_count,
                created_at
            )
            SELECT
                uri,
                author_display_name,
                author_handle,
                text,
                bookmark_count,
                like_count,
                quote_count,
                reply_count,
                repost_count,
                created_at
            FROM feed_posts
            WHERE source = 'bluesky'
            """
        )
    )

    op.drop_index("idx_feed_posts_author_handle", table_name="feed_posts")
    op.drop_table("feed_posts")

    with op.batch_alter_table("generated_feeds", schema=None) as batch_op:
        batch_op.alter_column("post_ids", new_column_name="post_uris")

    rows = conn.execute(
        sa.text(
            "SELECT agent_handle, run_id, turn_number, post_uris FROM generated_feeds"
        )
    ).fetchall()
    for row in rows:
        mapping = row._mapping
        raw = mapping["post_uris"]
        try:
            items = json.loads(raw) if raw is not None else []
        except json.JSONDecodeError:
            continue
        if not isinstance(items, list):
            continue
        new_items = [_strip_bluesky_prefix(str(item)) for item in items]
        if new_items == items:
            continue
        conn.execute(
            sa.text(
                """
                UPDATE generated_feeds
                SET post_uris = :post_uris
                WHERE agent_handle = :agent_handle AND run_id = :run_id AND turn_number = :turn_number
                """
            ),
            {
                "post_uris": json.dumps(new_items),
                "agent_handle": mapping["agent_handle"],
                "run_id": mapping["run_id"],
                "turn_number": mapping["turn_number"],
            },
        )

    conn.execute(
        sa.text(
            "UPDATE likes SET post_id = substr(post_id, length('bluesky:') + 1) WHERE post_id LIKE 'bluesky:%'"
        )
    )
    conn.execute(
        sa.text(
            "UPDATE comments SET post_id = substr(post_id, length('bluesky:') + 1) WHERE post_id LIKE 'bluesky:%'"
        )
    )
