"""add agent profile comments likes linked_agents tables

Revision ID: 16c6ae889cf1
Revises: d0a1b2c3d4e5
Create Date: 2026-02-23 20:24:01.729953

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "16c6ae889cf1"
down_revision: Union[str, Sequence[str], None] = "d0a1b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "agent_profile_comments",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("agent_id", sa.Text(), nullable=False),
        sa.Column("post_uri", sa.Text(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["agent_id"],
            ["agent.agent_id"],
            name="fk_agent_profile_comments_agent_id",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_agent_profile_comments"),
    )
    with op.batch_alter_table("agent_profile_comments", schema=None) as batch_op:
        batch_op.create_index(
            "idx_agent_profile_comments_agent_id", ["agent_id"], unique=False
        )

    op.create_table(
        "agent_liked_posts",
        sa.Column("agent_id", sa.Text(), nullable=False),
        sa.Column("post_uri", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["agent_id"],
            ["agent.agent_id"],
            name="fk_agent_liked_posts_agent_id",
        ),
        sa.PrimaryKeyConstraint("agent_id", "post_uri", name="pk_agent_liked_posts"),
    )

    op.create_table(
        "agent_linked_agents",
        sa.Column("agent_id", sa.Text(), nullable=False),
        sa.Column("linked_agent_handle", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["agent_id"],
            ["agent.agent_id"],
            name="fk_agent_linked_agents_agent_id",
        ),
        sa.PrimaryKeyConstraint(
            "agent_id", "linked_agent_handle", name="pk_agent_linked_agents"
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("agent_profile_comments", schema=None) as batch_op:
        batch_op.drop_index("idx_agent_profile_comments_agent_id", if_exists=True)
    op.drop_table("agent_profile_comments")
    op.drop_table("agent_linked_agents")
    op.drop_table("agent_liked_posts")
