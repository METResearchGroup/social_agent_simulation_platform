"""create agent tables

Revision ID: d0a1b2c3d4e5
Revises: c1f7e2d9a1b3
Create Date: 2026-02-19 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d0a1b2c3d4e5"
down_revision: Union[str, Sequence[str], None] = "c1f7e2d9a1b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "agent",
        sa.Column("agent_id", sa.Text(), nullable=False),
        sa.Column("handle", sa.Text(), nullable=False),
        sa.Column("persona_source", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("agent_id", name="pk_agent"),
        sa.UniqueConstraint("handle", name="uq_agent_handle"),
    )

    op.create_table(
        "agent_persona_bios",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("agent_id", sa.Text(), nullable=False),
        sa.Column("persona_bio", sa.Text(), nullable=False),
        sa.Column("persona_bio_source", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["agent_id"],
            ["agent.agent_id"],
            name="fk_agent_persona_bios_agent_id",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_agent_persona_bios"),
    )
    with op.batch_alter_table("agent_persona_bios", schema=None) as batch_op:
        batch_op.create_index(
            "idx_agent_persona_bios_agent_id_created_at",
            ["agent_id", "created_at"],
            unique=False,
        )

    op.create_table(
        "user_agent_profile_metadata",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("agent_id", sa.Text(), nullable=False),
        sa.Column("followers_count", sa.Integer(), nullable=False),
        sa.Column("follows_count", sa.Integer(), nullable=False),
        sa.Column("posts_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["agent_id"],
            ["agent.agent_id"],
            name="fk_user_agent_profile_metadata_agent_id",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_user_agent_profile_metadata"),
        sa.UniqueConstraint("agent_id", name="uq_user_agent_profile_metadata_agent_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("agent_persona_bios", schema=None) as batch_op:
        batch_op.drop_index(
            "idx_agent_persona_bios_agent_id_created_at",
            if_exists=True,
        )
    op.drop_table("user_agent_profile_metadata")
    op.drop_table("agent_persona_bios")
    op.drop_table("agent")
