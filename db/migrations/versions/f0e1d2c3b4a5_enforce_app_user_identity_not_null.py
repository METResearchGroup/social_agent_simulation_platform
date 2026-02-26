"""enforce app_user identity columns are required

Revision ID: f0e1d2c3b4a5
Revises: b5bf30f87165
Create Date: 2026-02-26 16:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f0e1d2c3b4a5"
down_revision: Union[str, Sequence[str], None] = "b5bf30f87165"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _ensure_no_missing_identity(conn: sa.Connection) -> None:
    row = conn.execute(
        sa.text(
            "SELECT COUNT(*) AS missing_count FROM app_users "
            "WHERE email IS NULL OR display_name IS NULL"
        )
    ).fetchone()
    missing = int(row[0]) if row is not None else 0
    if missing:
        raise RuntimeError(
            "Found %d app_users rows missing email/display_name; "
            "populate them before running this migration." % missing
        )


def upgrade() -> None:
    """Upgrade schema to require email/display_name."""
    conn = op.get_bind()
    assert isinstance(conn, sa.Connection)
    _ensure_no_missing_identity(conn)

    with op.batch_alter_table("app_users", schema=None) as batch_op:
        batch_op.alter_column(
            "email",
            existing_type=sa.Text(),
            nullable=False,
        )
        batch_op.alter_column(
            "display_name",
            existing_type=sa.Text(),
            nullable=False,
        )


def downgrade() -> None:
    """Downgrade schema to allow nullable identity fields again."""
    with op.batch_alter_table("app_users", schema=None) as batch_op:
        batch_op.alter_column(
            "display_name",
            existing_type=sa.Text(),
            nullable=True,
        )
        batch_op.alter_column(
            "email",
            existing_type=sa.Text(),
            nullable=True,
        )
