"""Add seed-state agent_follow_edges table.

Revision ID: 6f2b7c8d9e1a
Revises: e1f0d1c2b3a4
Create Date: 2026-03-13 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6f2b7c8d9e1a"
down_revision: Union[str, Sequence[str], None] = "e1f0d1c2b3a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the agent_follow_edges seed-state table and indexes."""
    op.create_table(
        "agent_follow_edges",
        sa.Column("agent_follow_edge_id", sa.Text(), nullable=False),
        sa.Column("follower_agent_id", sa.Text(), nullable=False),
        sa.Column("target_agent_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
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
        sa.CheckConstraint(
            "follower_agent_id != target_agent_id",
            name="ck_agent_follow_edges_no_self_follow",
        ),
    )
    op.create_index(
        "idx_agent_follow_edges_follower_agent_id",
        "agent_follow_edges",
        ["follower_agent_id"],
        unique=False,
    )
    op.create_index(
        "idx_agent_follow_edges_target_agent_id",
        "agent_follow_edges",
        ["target_agent_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop the agent_follow_edges seed-state table and indexes."""
    op.drop_index(
        "idx_agent_follow_edges_target_agent_id",
        table_name="agent_follow_edges",
    )
    op.drop_index(
        "idx_agent_follow_edges_follower_agent_id",
        table_name="agent_follow_edges",
    )
    op.drop_table("agent_follow_edges")
