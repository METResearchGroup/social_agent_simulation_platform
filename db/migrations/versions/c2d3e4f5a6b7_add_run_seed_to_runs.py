"""add run_seed to runs

Revision ID: c2d3e4f5a6b7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-19 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add run_seed column for reproducible simulation runs."""
    with op.batch_alter_table("runs", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("run_seed", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    """Remove run_seed column."""
    with op.batch_alter_table("runs", schema=None) as batch_op:
        batch_op.drop_column("run_seed")
