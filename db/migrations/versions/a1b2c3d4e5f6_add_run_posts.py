"""add run posts

Revision ID: a1b2c3d4e5f6
Revises: 7b363560da3c
Create Date: 2026-03-17 14:00:00.000000

"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "7b363560da3c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "run_posts",
        sa.Column("run_post_id", sa.Text(), nullable=False),
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("agent_post_id", sa.Text(), nullable=False),
        sa.Column("author_agent_id", sa.Text(), nullable=False),
        sa.Column("author_handle_at_start", sa.Text(), nullable=False),
        sa.Column("author_display_name_at_start", sa.Text(), nullable=False),
        sa.Column("body_text_at_start", sa.Text(), nullable=False),
        sa.Column("published_at_start", sa.Text(), nullable=False),
        sa.Column("source_post_id_at_start", sa.Text(), nullable=True),
        sa.Column("source_at_start", sa.Text(), nullable=True),
        sa.Column("source_uri_at_start", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["runs.run_id"],
            name="fk_run_posts_run_id",
        ),
        sa.ForeignKeyConstraint(
            ["run_id", "author_agent_id"],
            ["run_agents.run_id", "run_agents.agent_id"],
            name="fk_run_posts_run_author",
        ),
        sa.PrimaryKeyConstraint("run_post_id", name="pk_run_posts"),
        sa.UniqueConstraint(
            "run_id",
            "agent_post_id",
            name="uq_run_posts_run_agent_post",
        ),
    )
    with op.batch_alter_table("run_posts") as batch_op:
        batch_op.create_index(
            "idx_run_posts_run_id",
            ["run_id"],
            unique=False,
        )
        batch_op.create_index(
            "idx_run_posts_run_author_published",
            ["run_id", "author_agent_id", "published_at_start"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("run_posts") as batch_op:
        batch_op.drop_index("idx_run_posts_run_author_published")
        batch_op.drop_index("idx_run_posts_run_id")
    op.drop_table("run_posts")
