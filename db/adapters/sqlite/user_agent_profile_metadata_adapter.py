"""SQLite implementation of user agent profile metadata database adapter.

EXTENSION: For caching or async, consider a caching layer around
get_metadata_by_agent_ids or an async batch loader (e.g. DataLoader).
"""

import sqlite3
from collections.abc import Iterable

from db.adapters.base import UserAgentProfileMetadataDatabaseAdapter
from db.adapters.sqlite.schema_utils import ordered_column_names, required_column_names
from db.adapters.sqlite.sqlite import validate_required_fields
from db.schema import user_agent_profile_metadata
from lib.validation_utils import validate_non_empty_string
from simulation.core.models.user_agent_profile_metadata import UserAgentProfileMetadata

METADATA_COLUMNS = ordered_column_names(user_agent_profile_metadata)
METADATA_REQUIRED_FIELDS = required_column_names(user_agent_profile_metadata)
_INSERT_METADATA_SQL = (
    f"INSERT OR REPLACE INTO user_agent_profile_metadata ({', '.join(METADATA_COLUMNS)}) "
    f"VALUES ({', '.join('?' for _ in METADATA_COLUMNS)})"
)


class SQLiteUserAgentProfileMetadataAdapter(UserAgentProfileMetadataDatabaseAdapter):
    """SQLite implementation of UserAgentProfileMetadataDatabaseAdapter."""

    def _validate_metadata_row(self, row: sqlite3.Row) -> None:
        """Validate that all required metadata fields are not NULL."""
        validate_required_fields(row, METADATA_REQUIRED_FIELDS)

    def _row_to_metadata(self, row: sqlite3.Row) -> UserAgentProfileMetadata:
        """Convert a database row to a UserAgentProfileMetadata model."""
        return UserAgentProfileMetadata(
            id=row["id"],
            agent_id=row["agent_id"],
            followers_count=row["followers_count"],
            follows_count=row["follows_count"],
            posts_count=row["posts_count"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def write_user_agent_profile_metadata(
        self, metadata: UserAgentProfileMetadata, *, conn: sqlite3.Connection
    ) -> None:
        """Write user agent profile metadata to SQLite.

        Raises:
            sqlite3.IntegrityError: If constraints are violated
            sqlite3.OperationalError: If database operation fails
        """
        row_values = tuple(getattr(metadata, col) for col in METADATA_COLUMNS)
        conn.execute(_INSERT_METADATA_SQL, row_values)

    def read_by_agent_id(
        self, agent_id: str, *, conn: sqlite3.Connection
    ) -> UserAgentProfileMetadata | None:
        """Read metadata by agent_id."""
        validate_non_empty_string(agent_id, "agent_id")
        row = conn.execute(
            "SELECT * FROM user_agent_profile_metadata WHERE agent_id = ?",
            (agent_id,),
        ).fetchone()
        if row is None:
            return None
        self._validate_metadata_row(row)
        return self._row_to_metadata(row)

    def read_metadata_by_agent_ids(
        self, agent_ids: Iterable[str], *, conn: sqlite3.Connection
    ) -> dict[str, UserAgentProfileMetadata | None]:
        """Read metadata for the given agent IDs."""
        agent_ids_list = list(agent_ids)
        if not agent_ids_list:
            return {}
        q_marks = ",".join("?" for _ in agent_ids_list)
        sql = f"SELECT * FROM user_agent_profile_metadata WHERE agent_id IN ({q_marks})"
        rows = conn.execute(sql, tuple(agent_ids_list)).fetchall()
        result: dict[str, UserAgentProfileMetadata | None] = {
            aid: None for aid in agent_ids_list
        }
        for row in rows:
            self._validate_metadata_row(row)
            result[row["agent_id"]] = self._row_to_metadata(row)
        return result

    def delete_by_agent_id(self, agent_id: str, *, conn: sqlite3.Connection) -> None:
        """Delete metadata by agent_id."""
        validate_non_empty_string(agent_id, "agent_id")
        conn.execute(
            "DELETE FROM user_agent_profile_metadata WHERE agent_id = ?",
            (agent_id,),
        )
