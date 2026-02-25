"""Enforce action uniqueness and drop redundant indexes.

Revision ID: c3a1d2e4f5a6
Revises: b8e4d1f2a3c6
Create Date: 2026-02-25 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3a1d2e4f5a6"
down_revision: Union[str, Sequence[str], None] = "b8e4d1f2a3c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _ensure_index(
    *,
    conn: sa.Connection,
    name: str,
    table: str,
    columns: list[str],
) -> None:
    existing = conn.execute(
        sa.text("SELECT name FROM sqlite_master WHERE type='index' AND name = :name"),
        {"name": name},
    ).fetchone()
    if existing is not None:
        return

    # This should be uncommon: batch mode generally preserves indexes. If an index
    # is missing, recreate it to maintain query performance parity.
    op.create_index(name, table, columns)


def upgrade() -> None:
    """Add composite uniqueness + drop redundant two-column indexes."""
    # Drop redundant (run_id, turn_number) indexes; the existing
    # (run_id, turn_number, agent_handle) indexes cover this prefix.
    op.drop_index("idx_likes_run_turn", table_name="likes")
    op.drop_index("idx_comments_run_turn", table_name="comments")
    op.drop_index("idx_follows_run_turn", table_name="follows")

    # Add composite unique constraints to prevent duplicate actions per turn.
    #
    # SQLite cannot add constraints via ALTER TABLE, so we use batch mode.
    with op.batch_alter_table("likes", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "uq_likes_run_turn_agent_post",
            ["run_id", "turn_number", "agent_handle", "post_id"],
        )
    with op.batch_alter_table("comments", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "uq_comments_run_turn_agent_post",
            ["run_id", "turn_number", "agent_handle", "post_id"],
        )
    with op.batch_alter_table("follows", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "uq_follows_run_turn_agent_user",
            ["run_id", "turn_number", "agent_handle", "user_id"],
        )

    # Defensive: ensure the covering indexes still exist after batch rebuild.
    # (Batch operations should preserve indexes, but this catches unexpected drift.)
    conn = op.get_bind()
    assert isinstance(conn, sa.Connection)
    _ensure_index(
        conn=conn,
        name="idx_likes_run_turn_agent",
        table="likes",
        columns=["run_id", "turn_number", "agent_handle"],
    )
    _ensure_index(
        conn=conn,
        name="idx_comments_run_turn_agent",
        table="comments",
        columns=["run_id", "turn_number", "agent_handle"],
    )
    _ensure_index(
        conn=conn,
        name="idx_follows_run_turn_agent",
        table="follows",
        columns=["run_id", "turn_number", "agent_handle"],
    )


def downgrade() -> None:
    """Remove composite uniqueness + restore dropped indexes."""
    with op.batch_alter_table("follows", schema=None) as batch_op:
        batch_op.drop_constraint("uq_follows_run_turn_agent_user", type_="unique")
    with op.batch_alter_table("comments", schema=None) as batch_op:
        batch_op.drop_constraint("uq_comments_run_turn_agent_post", type_="unique")
    with op.batch_alter_table("likes", schema=None) as batch_op:
        batch_op.drop_constraint("uq_likes_run_turn_agent_post", type_="unique")

    op.create_index("idx_likes_run_turn", "likes", ["run_id", "turn_number"])
    op.create_index("idx_comments_run_turn", "comments", ["run_id", "turn_number"])
    op.create_index("idx_follows_run_turn", "follows", ["run_id", "turn_number"])
