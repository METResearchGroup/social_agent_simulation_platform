"""add run_agents table

Revision ID: 6a7b8c9d0e1f
Revises: e1f0d1c2b3a4
Create Date: 2026-03-13 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6a7b8c9d0e1f"
down_revision: Union[str, Sequence[str], None] = "e1f0d1c2b3a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "run_agents",
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("agent_id", sa.Text(), nullable=False),
        sa.Column("selection_order", sa.Integer(), nullable=False),
        sa.Column("handle_at_start", sa.Text(), nullable=False),
        sa.Column("display_name_at_start", sa.Text(), nullable=False),
        sa.Column("persona_bio_at_start", sa.Text(), nullable=False),
        sa.Column("followers_count_at_start", sa.Integer(), nullable=False),
        sa.Column("follows_count_at_start", sa.Integer(), nullable=False),
        sa.Column("posts_count_at_start", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["runs.run_id"],
            name="fk_run_agents_run_id",
        ),
        sa.ForeignKeyConstraint(
            ["agent_id"],
            ["agent.agent_id"],
            name="fk_run_agents_agent_id",
        ),
        sa.PrimaryKeyConstraint("run_id", "agent_id", name="pk_run_agents"),
        sa.UniqueConstraint(
            "run_id",
            "selection_order",
            name="uq_run_agents_run_selection_order",
        ),
    )
    with op.batch_alter_table("run_agents", schema=None) as batch_op:
        batch_op.create_index("idx_run_agents_run_id", ["run_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("run_agents", schema=None) as batch_op:
        batch_op.drop_index("idx_run_agents_run_id")
    op.drop_table("run_agents")
