"""add agent follow edges

Revision ID: d31fef7e41c3
Revises: 6a7b8c9d0e1f
Create Date: 2026-03-17 14:46:54.879594

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d31fef7e41c3"
down_revision: Union[str, Sequence[str], None] = "6a7b8c9d0e1f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "agent_follow_edges",
        sa.Column("agent_follow_edge_id", sa.Text(), nullable=False),
        sa.Column("follower_agent_id", sa.Text(), nullable=False),
        sa.Column("target_agent_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "follower_agent_id != target_agent_id",
            name="ck_agent_follow_edges_no_self_follow",
        ),
        sa.ForeignKeyConstraint(
            ["follower_agent_id"],
            ["agent.agent_id"],
            name="fk_agent_follow_edges_follower_agent_id",
        ),
        sa.ForeignKeyConstraint(
            ["target_agent_id"],
            ["agent.agent_id"],
            name="fk_agent_follow_edges_target_agent_id",
        ),
        sa.PrimaryKeyConstraint(
            "agent_follow_edge_id",
            name="pk_agent_follow_edges",
        ),
        sa.UniqueConstraint(
            "follower_agent_id",
            "target_agent_id",
            name="uq_agent_follow_edges_follower_target",
        ),
    )
    with op.batch_alter_table("agent_follow_edges") as batch_op:
        batch_op.create_index(
            "idx_agent_follow_edges_follower_agent_id",
            ["follower_agent_id"],
            unique=False,
        )
        batch_op.create_index(
            "idx_agent_follow_edges_target_agent_id",
            ["target_agent_id"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("agent_follow_edges") as batch_op:
        batch_op.drop_index("idx_agent_follow_edges_target_agent_id")
        batch_op.drop_index("idx_agent_follow_edges_follower_agent_id")
    op.drop_table("agent_follow_edges")
