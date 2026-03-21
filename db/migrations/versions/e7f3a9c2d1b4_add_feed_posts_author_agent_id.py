"""Add feed_posts.author_agent_id (FK to agent) with backfill.

Revision ID: e7f3a9c2d1b4
Revises: d4f8a1c3e5b7
Create Date: 2026-03-21 12:00:00.000000

Adds ``author_agent_id`` to ``feed_posts``, backfills via
``feed_posts.author_handle = agent.handle``, deletes rows with no matching
agent (orphan catalog posts), then enforces NOT NULL and FK to ``agent.agent_id``.

Downgrade is intentionally unsupported (restore from backup).
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e7f3a9c2d1b4"
down_revision: Union[str, Sequence[str], None] = "d4f8a1c3e5b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("PRAGMA foreign_keys=OFF"))
    try:
        with op.batch_alter_table("feed_posts", schema=None) as batch_op:
            batch_op.add_column(sa.Column("author_agent_id", sa.Text(), nullable=True))

        conn.execute(
            sa.text(
                """
                UPDATE feed_posts
                SET author_agent_id = (
                    SELECT a.agent_id
                    FROM agent AS a
                    WHERE a.handle = feed_posts.author_handle
                )
                """
            )
        )

        conn.execute(sa.text("DELETE FROM feed_posts WHERE author_agent_id IS NULL"))

        with op.batch_alter_table("feed_posts", schema=None) as batch_op:
            batch_op.alter_column("author_agent_id", nullable=False)
            batch_op.create_foreign_key(
                "fk_feed_posts_author_agent_id",
                "agent",
                ["author_agent_id"],
                ["agent_id"],
            )

        op.create_index(
            "idx_feed_posts_author_agent_id",
            "feed_posts",
            ["author_agent_id"],
            unique=False,
        )
    finally:
        conn.execute(sa.text("PRAGMA foreign_keys=ON"))


def downgrade() -> None:
    raise NotImplementedError("Downgrade unsupported; restore from backup.")
