"""add feed_algorithm to runs

Revision ID: 9b6a9fe63ec1
Revises: 4ea9cc982076
Create Date: 2026-02-17 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9b6a9fe63ec1"
down_revision: Union[str, Sequence[str], None] = "4ea9cc982076"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_FEED_ALGORITHM: str = "chronological"


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("runs", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "feed_algorithm",
                sa.Text(),
                nullable=False,
                server_default=sa.text(f"'{DEFAULT_FEED_ALGORITHM}'"),
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("runs", schema=None) as batch_op:
        batch_op.drop_column("feed_algorithm")
