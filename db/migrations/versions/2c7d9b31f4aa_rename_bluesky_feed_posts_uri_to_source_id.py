"""rename bluesky_feed_posts.uri to source_id

Revision ID: 2c7d9b31f4aa
Revises: f0e1d2c3b4a5
Create Date: 2026-03-08 13:46:00.000000

Rationale:
The column previously named `uri` is the source-platform's native identifier for a post.
For Bluesky this is an AT Protocol URI, but the identifier concept is not inherently
URI-shaped across all possible post sources. Rename to `source_id` to make the schema
platform-agnostic with zero data changes.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2c7d9b31f4aa"
down_revision: Union[str, Sequence[str], None] = "f0e1d2c3b4a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
    try:
        with op.batch_alter_table("bluesky_feed_posts", schema=None) as batch_op:
            batch_op.alter_column("uri", new_column_name="source_id")
    finally:
        conn.exec_driver_sql("PRAGMA foreign_keys=ON")


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
    try:
        with op.batch_alter_table("bluesky_feed_posts", schema=None) as batch_op:
            batch_op.alter_column("source_id", new_column_name="uri")
    finally:
        conn.exec_driver_sql("PRAGMA foreign_keys=ON")
