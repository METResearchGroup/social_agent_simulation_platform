"""add agent post comments and run post comments

Revision ID: b2c4d6e8f0a1
Revises: 1a03b3eb67f9
Create Date: 2026-03-19 12:00:00.000000

"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c4d6e8f0a1"
down_revision: str | Sequence[str] | None = "1a03b3eb67f9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "agent_post_comments",
        sa.Column("agent_post_comment_id", sa.Text(), nullable=False),
        sa.Column("agent_post_id", sa.Text(), nullable=False),
        sa.Column("author_agent_id", sa.Text(), nullable=False),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.Column("published_at", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["agent_post_id"],
            ["agent_posts.agent_post_id"],
            name="fk_agent_post_comments_agent_post_id",
        ),
        sa.ForeignKeyConstraint(
            ["author_agent_id"],
            ["agent.agent_id"],
            name="fk_agent_post_comments_author_agent_id",
        ),
        sa.PrimaryKeyConstraint("agent_post_comment_id", name="pk_agent_post_comments"),
    )
    with op.batch_alter_table("agent_post_comments") as batch_op:
        batch_op.create_index(
            "idx_agent_post_comments_post_published",
            ["agent_post_id", "published_at"],
            unique=False,
        )
        batch_op.create_index(
            "idx_agent_post_comments_author_published",
            ["author_agent_id", "published_at"],
            unique=False,
        )

    # Composite unique on run_posts required for composite FK: comments must reference
    # a post that belongs to the same run.
    with op.batch_alter_table("run_posts", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "uq_run_posts_run_post",
            ["run_id", "run_post_id"],
        )

    op.create_table(
        "run_post_comments",
        sa.Column("run_post_comment_id", sa.Text(), nullable=False),
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("run_post_id", sa.Text(), nullable=False),
        sa.Column("author_agent_id", sa.Text(), nullable=False),
        sa.Column("author_handle_at_start", sa.Text(), nullable=False),
        sa.Column("author_display_name_at_start", sa.Text(), nullable=False),
        sa.Column("body_text_at_start", sa.Text(), nullable=False),
        sa.Column("published_at_start", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["runs.run_id"],
            name="fk_run_post_comments_run_id",
        ),
        sa.ForeignKeyConstraint(
            ["run_post_id"],
            ["run_posts.run_post_id"],
            name="fk_run_post_comments_run_post_id",
        ),
        sa.ForeignKeyConstraint(
            ["run_id", "run_post_id"],
            ["run_posts.run_id", "run_posts.run_post_id"],
            name="fk_run_post_comments_run_post",
        ),
        sa.ForeignKeyConstraint(
            ["run_id", "author_agent_id"],
            ["run_agents.run_id", "run_agents.agent_id"],
            name="fk_run_post_comments_run_author",
        ),
        sa.PrimaryKeyConstraint("run_post_comment_id", name="pk_run_post_comments"),
    )
    with op.batch_alter_table("run_post_comments", schema=None) as batch_op:
        batch_op.create_index(
            "idx_run_post_comments_run_post_published",
            ["run_id", "run_post_id", "published_at_start"],
            unique=False,
        )
        batch_op.create_index(
            "idx_run_post_comments_run_author_published",
            ["run_id", "author_agent_id", "published_at_start"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("run_post_comments", schema=None) as batch_op:
        batch_op.drop_index("idx_run_post_comments_run_author_published")
        batch_op.drop_index("idx_run_post_comments_run_post_published")
    op.drop_table("run_post_comments")

    with op.batch_alter_table("run_posts", schema=None) as batch_op:
        batch_op.drop_constraint("uq_run_posts_run_post", type_="unique")

    with op.batch_alter_table("agent_post_comments") as batch_op:
        batch_op.drop_index("idx_agent_post_comments_author_published")
        batch_op.drop_index("idx_agent_post_comments_post_published")
    op.drop_table("agent_post_comments")
