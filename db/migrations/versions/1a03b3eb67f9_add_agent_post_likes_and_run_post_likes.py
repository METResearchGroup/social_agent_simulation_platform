"""add agent post likes and run post likes

Revision ID: 1a03b3eb67f9
Revises: a1b2c3d4e5f6
Create Date: 2026-03-19 10:00:00.000000

"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1a03b3eb67f9"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "agent_post_likes",
        sa.Column("agent_post_like_id", sa.Text(), nullable=False),
        sa.Column("agent_post_id", sa.Text(), nullable=False),
        sa.Column("liker_agent_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["agent_post_id"],
            ["agent_posts.agent_post_id"],
            name="fk_agent_post_likes_agent_post_id",
        ),
        sa.ForeignKeyConstraint(
            ["liker_agent_id"],
            ["agent.agent_id"],
            name="fk_agent_post_likes_liker_agent_id",
        ),
        sa.PrimaryKeyConstraint("agent_post_like_id", name="pk_agent_post_likes"),
        sa.UniqueConstraint(
            "liker_agent_id",
            "agent_post_id",
            name="uq_agent_post_likes_liker_agent_post",
        ),
    )
    with op.batch_alter_table("agent_post_likes") as batch_op:
        batch_op.create_index(
            "idx_agent_post_likes_post_id",
            ["agent_post_id"],
            unique=False,
        )

    op.create_table(
        "run_post_likes",
        sa.Column("run_post_like_id", sa.Text(), nullable=False),
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("run_post_id", sa.Text(), nullable=False),
        sa.Column("liker_agent_id", sa.Text(), nullable=False),
        sa.Column("liker_handle_at_start", sa.Text(), nullable=False),
        sa.Column("liker_display_name_at_start", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["runs.run_id"],
            name="fk_run_post_likes_run_id",
        ),
        sa.ForeignKeyConstraint(
            ["run_post_id"],
            ["run_posts.run_post_id"],
            name="fk_run_post_likes_run_post_id",
        ),
        sa.ForeignKeyConstraint(
            ["run_id", "liker_agent_id"],
            ["run_agents.run_id", "run_agents.agent_id"],
            name="fk_run_post_likes_run_liker",
        ),
        sa.PrimaryKeyConstraint("run_post_like_id", name="pk_run_post_likes"),
        sa.UniqueConstraint(
            "run_id",
            "liker_agent_id",
            "run_post_id",
            name="uq_run_post_likes_run_liker_post",
        ),
    )
    with op.batch_alter_table("run_post_likes", schema=None) as batch_op:
        batch_op.create_index(
            "idx_run_post_likes_run_post",
            ["run_id", "run_post_id"],
            unique=False,
        )
        batch_op.create_index(
            "idx_run_post_likes_run_liker",
            ["run_id", "liker_agent_id"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("run_post_likes", schema=None) as batch_op:
        batch_op.drop_index("idx_run_post_likes_run_liker")
        batch_op.drop_index("idx_run_post_likes_run_post")
    op.drop_table("run_post_likes")

    with op.batch_alter_table("agent_post_likes") as batch_op:
        batch_op.drop_index("idx_agent_post_likes_post_id")
    op.drop_table("agent_post_likes")
