"""Add agent-scoped seed action tables.

Revision ID: e2f4a6c8d0b1
Revises: c3a1d2e4f5a6
Create Date: 2026-02-25 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e2f4a6c8d0b1"
down_revision: Union[str, Sequence[str], None] = "c3a1d2e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create agent-scoped seed action tables for Create Agent fast-follows."""
    op.create_table(
        "agent_seed_likes",
        sa.Column("seed_like_id", sa.Text(), nullable=False),
        sa.Column("agent_handle", sa.Text(), nullable=False),
        sa.Column("post_uri", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("seed_like_id", name="pk_agent_seed_likes"),
        sa.ForeignKeyConstraint(
            ["agent_handle"],
            ["agent.handle"],
            name="fk_agent_seed_likes_agent_handle",
        ),
        sa.UniqueConstraint(
            "agent_handle",
            "post_uri",
            name="uq_agent_seed_likes_agent_handle_post_uri",
        ),
    )
    op.create_index(
        "idx_agent_seed_likes_agent_handle", "agent_seed_likes", ["agent_handle"]
    )

    op.create_table(
        "agent_seed_comments",
        sa.Column("seed_comment_id", sa.Text(), nullable=False),
        sa.Column("agent_handle", sa.Text(), nullable=False),
        sa.Column("post_uri", sa.Text(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("seed_comment_id", name="pk_agent_seed_comments"),
        sa.ForeignKeyConstraint(
            ["agent_handle"],
            ["agent.handle"],
            name="fk_agent_seed_comments_agent_handle",
        ),
    )
    op.create_index(
        "idx_agent_seed_comments_agent_handle",
        "agent_seed_comments",
        ["agent_handle"],
    )

    op.create_table(
        "agent_seed_follows",
        sa.Column("seed_follow_id", sa.Text(), nullable=False),
        sa.Column("agent_handle", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("seed_follow_id", name="pk_agent_seed_follows"),
        sa.ForeignKeyConstraint(
            ["agent_handle"],
            ["agent.handle"],
            name="fk_agent_seed_follows_agent_handle",
        ),
        sa.UniqueConstraint(
            "agent_handle",
            "user_id",
            name="uq_agent_seed_follows_agent_handle_user_id",
        ),
    )
    op.create_index(
        "idx_agent_seed_follows_agent_handle",
        "agent_seed_follows",
        ["agent_handle"],
    )


def downgrade() -> None:
    """Drop agent-scoped seed action tables."""
    op.drop_index(
        "idx_agent_seed_follows_agent_handle", table_name="agent_seed_follows"
    )
    op.drop_table("agent_seed_follows")

    op.drop_index(
        "idx_agent_seed_comments_agent_handle", table_name="agent_seed_comments"
    )
    op.drop_table("agent_seed_comments")

    op.drop_index("idx_agent_seed_likes_agent_handle", table_name="agent_seed_likes")
    op.drop_table("agent_seed_likes")
