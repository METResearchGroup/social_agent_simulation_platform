"""add agent posts

Revision ID: 7b363560da3c
Revises: 8f6c2a1b4d3e
Create Date: 2026-03-17 13:37:00.610644

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7b363560da3c"
down_revision: Union[str, Sequence[str], None] = "8f6c2a1b4d3e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "agent_posts",
        sa.Column("agent_post_id", sa.Text(), nullable=False),
        sa.Column("agent_id", sa.Text(), nullable=False),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.Column("published_at", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.Column("source_post_id", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("source_uri", sa.Text(), nullable=True),
        sa.Column("imported_author_handle", sa.Text(), nullable=True),
        sa.Column("imported_author_display_name", sa.Text(), nullable=True),
        sa.Column("import_metadata_json", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "(source IS NULL AND source_post_id IS NULL) OR "
            "(source IS NOT NULL AND source_post_id IS NOT NULL)",
            name="ck_agent_posts_source_pair",
        ),
        sa.ForeignKeyConstraint(
            ["agent_id"],
            ["agent.agent_id"],
            name="fk_agent_posts_agent_id",
        ),
        sa.PrimaryKeyConstraint(
            "agent_post_id",
            name="pk_agent_posts",
        ),
        sa.UniqueConstraint(
            "source",
            "source_post_id",
            name="uq_agent_posts_source_source_post_id",
        ),
    )
    with op.batch_alter_table("agent_posts") as batch_op:
        batch_op.create_index(
            "idx_agent_posts_agent_id_published_at",
            ["agent_id", "published_at"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("agent_posts") as batch_op:
        batch_op.drop_index("idx_agent_posts_agent_id_published_at")
    op.drop_table("agent_posts")
