"""add metrics tables

Revision ID: c1f7e2d9a1b3
Revises: 9b6a9fe63ec1
Create Date: 2026-02-18 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c1f7e2d9a1b3"
down_revision: Union[str, Sequence[str], None] = "9b6a9fe63ec1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "turn_metrics",
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("turn_number", sa.Integer(), nullable=False),
        sa.Column("metrics", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "turn_number >= 0", name="ck_turn_metrics_turn_number_gte_0"
        ),
        sa.ForeignKeyConstraint(
            ["run_id"], ["runs.run_id"], name="fk_turn_metrics_run_id"
        ),
        sa.PrimaryKeyConstraint("run_id", "turn_number", name="pk_turn_metrics"),
    )
    with op.batch_alter_table("turn_metrics", schema=None) as batch_op:
        batch_op.create_index("idx_turn_metrics_run_id", ["run_id"], unique=False)

    op.create_table(
        "run_metrics",
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("metrics", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"], ["runs.run_id"], name="fk_run_metrics_run_id"
        ),
        sa.PrimaryKeyConstraint("run_id", name="pk_run_metrics"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("turn_metrics", schema=None) as batch_op:
        batch_op.drop_index("idx_turn_metrics_run_id")
    op.drop_table("run_metrics")
    op.drop_table("turn_metrics")
