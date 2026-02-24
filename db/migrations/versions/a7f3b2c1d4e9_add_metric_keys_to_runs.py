"""add metric_keys to runs

Revision ID: a7f3b2c1d4e9
Revises: d0a1b2c3d4e5
Create Date: 2026-02-23 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7f3b2c1d4e9"
down_revision: Union[str, Sequence[str], None] = "d0a1b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_METRIC_KEYS_JSON: str = (
    '["run.actions.total","run.actions.total_by_type",'
    '"turn.actions.counts_by_type","turn.actions.total"]'
)


def upgrade() -> None:
    """Upgrade schema: add metric_keys column and backfill NULLs."""
    with op.batch_alter_table("runs", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("metric_keys", sa.Text(), nullable=True),
        )

    # Backfill existing rows where metric_keys IS NULL.
    op.execute(
        f"UPDATE runs SET metric_keys = '{DEFAULT_METRIC_KEYS_JSON}' "
        "WHERE metric_keys IS NULL"
    )


def downgrade() -> None:
    """Downgrade schema: remove metric_keys column."""
    with op.batch_alter_table("runs", schema=None) as batch_op:
        batch_op.drop_column("metric_keys")
