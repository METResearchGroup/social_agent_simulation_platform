"""add run follow edges

Revision ID: 8f6c2a1b4d3e
Revises: d31fef7e41c3
Create Date: 2026-03-17 17:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8f6c2a1b4d3e"
down_revision: Union[str, Sequence[str], None] = "d31fef7e41c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "run_follow_edges",
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("follower_agent_id", sa.Text(), nullable=False),
        sa.Column("target_agent_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "follower_agent_id != target_agent_id",
            name="ck_run_follow_edges_no_self_follow",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["runs.run_id"],
            name="fk_run_follow_edges_run_id",
        ),
        sa.ForeignKeyConstraint(
            ["run_id", "follower_agent_id"],
            ["run_agents.run_id", "run_agents.agent_id"],
            name="fk_run_follow_edges_follower_run_agent",
        ),
        sa.ForeignKeyConstraint(
            ["run_id", "target_agent_id"],
            ["run_agents.run_id", "run_agents.agent_id"],
            name="fk_run_follow_edges_target_run_agent",
        ),
        sa.PrimaryKeyConstraint(
            "run_id",
            "follower_agent_id",
            "target_agent_id",
            name="pk_run_follow_edges",
        ),
    )
    with op.batch_alter_table("run_follow_edges", schema=None) as batch_op:
        batch_op.create_index("idx_run_follow_edges_run_id", ["run_id"], unique=False)
        batch_op.create_index(
            "idx_run_follow_edges_run_follower",
            ["run_id", "follower_agent_id"],
            unique=False,
        )
        batch_op.create_index(
            "idx_run_follow_edges_run_target",
            ["run_id", "target_agent_id"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("run_follow_edges", schema=None) as batch_op:
        batch_op.drop_index("idx_run_follow_edges_run_target")
        batch_op.drop_index("idx_run_follow_edges_run_follower")
        batch_op.drop_index("idx_run_follow_edges_run_id")
    op.drop_table("run_follow_edges")
