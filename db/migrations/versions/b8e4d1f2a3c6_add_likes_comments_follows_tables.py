"""add likes comments follows tables

Revision ID: b8e4d1f2a3c6
Revises: a7f3b2c1d4e9
Create Date: 2026-02-24 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8e4d1f2a3c6"
down_revision: Union[str, Sequence[str], None] = "a7f3b2c1d4e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create likes, comments, follows tables and indexes."""
    op.create_table(
        "likes",
        sa.Column("like_id", sa.Text(), nullable=False),
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("turn_number", sa.Integer(), nullable=False),
        sa.Column("agent_handle", sa.Text(), nullable=False),
        sa.Column("post_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("model_used", sa.Text(), nullable=True),
        sa.Column("generation_metadata_json", sa.Text(), nullable=True),
        sa.Column("generation_created_at", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["runs.run_id"], name="fk_likes_run_id"),
        sa.PrimaryKeyConstraint("like_id", name="pk_likes"),
        sa.CheckConstraint("turn_number >= 0", name="ck_likes_turn_number_gte_0"),
    )
    op.create_index("idx_likes_run_turn", "likes", ["run_id", "turn_number"])
    op.create_index(
        "idx_likes_run_turn_agent", "likes", ["run_id", "turn_number", "agent_handle"]
    )

    op.create_table(
        "comments",
        sa.Column("comment_id", sa.Text(), nullable=False),
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("turn_number", sa.Integer(), nullable=False),
        sa.Column("agent_handle", sa.Text(), nullable=False),
        sa.Column("post_id", sa.Text(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("model_used", sa.Text(), nullable=True),
        sa.Column("generation_metadata_json", sa.Text(), nullable=True),
        sa.Column("generation_created_at", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["runs.run_id"], name="fk_comments_run_id"),
        sa.PrimaryKeyConstraint("comment_id", name="pk_comments"),
        sa.CheckConstraint("turn_number >= 0", name="ck_comments_turn_number_gte_0"),
    )
    op.create_index("idx_comments_run_turn", "comments", ["run_id", "turn_number"])
    op.create_index(
        "idx_comments_run_turn_agent",
        "comments",
        ["run_id", "turn_number", "agent_handle"],
    )

    op.create_table(
        "follows",
        sa.Column("follow_id", sa.Text(), nullable=False),
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("turn_number", sa.Integer(), nullable=False),
        sa.Column("agent_handle", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("model_used", sa.Text(), nullable=True),
        sa.Column("generation_metadata_json", sa.Text(), nullable=True),
        sa.Column("generation_created_at", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["runs.run_id"], name="fk_follows_run_id"),
        sa.PrimaryKeyConstraint("follow_id", name="pk_follows"),
        sa.CheckConstraint("turn_number >= 0", name="ck_follows_turn_number_gte_0"),
    )
    op.create_index("idx_follows_run_turn", "follows", ["run_id", "turn_number"])
    op.create_index(
        "idx_follows_run_turn_agent",
        "follows",
        ["run_id", "turn_number", "agent_handle"],
    )


def downgrade() -> None:
    """Drop likes, comments, follows tables and indexes."""
    op.drop_index("idx_follows_run_turn_agent", table_name="follows")
    op.drop_index("idx_follows_run_turn", table_name="follows")
    op.drop_table("follows")

    op.drop_index("idx_comments_run_turn_agent", table_name="comments")
    op.drop_index("idx_comments_run_turn", table_name="comments")
    op.drop_table("comments")

    op.drop_index("idx_likes_run_turn_agent", table_name="likes")
    op.drop_index("idx_likes_run_turn", table_name="likes")
    op.drop_table("likes")
