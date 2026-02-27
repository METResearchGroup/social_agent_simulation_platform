"""add app_users and run app_user references

Revision ID: b5bf30f87165
Revises: c3a1d2e4f5a6
Create Date: 2026-02-26 14:56:45.483079

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b5bf30f87165"
down_revision: Union[str, Sequence[str], None] = "c3a1d2e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "app_users",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("auth_provider_id", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("display_name", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("last_seen_at", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("app_users", schema=None) as batch_op:
        batch_op.create_index(
            "idx_app_users_auth_provider_id",
            ["auth_provider_id"],
            unique=True,
        )

    with op.batch_alter_table("runs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("app_user_id", sa.Text(), nullable=True))
        batch_op.create_index(
            "idx_runs_app_user_id",
            ["app_user_id"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("runs", schema=None) as batch_op:
        batch_op.drop_index("idx_runs_app_user_id")
        batch_op.drop_column("app_user_id")

    with op.batch_alter_table("app_users", schema=None) as batch_op:
        batch_op.drop_index("idx_app_users_auth_provider_id")

    op.drop_table("app_users")
