"""SQLite implementation of agent persona bio database adapter.

TODO: For caching or async, consider a caching layer around
read_latest_bios_by_agent_ids or an async batch loader (e.g. DataLoader).
"""

import sqlite3
from collections.abc import Iterable

from db.adapters.base import AgentBioDatabaseAdapter
from db.adapters.sqlite.schema_utils import ordered_column_names, required_column_names
from db.adapters.sqlite.sqlite import validate_required_fields
from db.schema import agent_persona_bios
from lib.validation_utils import validate_non_empty_string
from simulation.core.models.agent_bio import AgentBio, PersonaBioSource

AGENT_BIO_COLUMNS = ordered_column_names(agent_persona_bios)
AGENT_BIO_REQUIRED_FIELDS = required_column_names(agent_persona_bios)
_INSERT_AGENT_BIO_SQL = (
    f"INSERT INTO agent_persona_bios ({', '.join(AGENT_BIO_COLUMNS)}) "
    f"VALUES ({', '.join('?' for _ in AGENT_BIO_COLUMNS)})"
)


class SQLiteAgentBioAdapter(AgentBioDatabaseAdapter):
    """SQLite implementation of AgentBioDatabaseAdapter."""

    def _validate_agent_bio_row(self, row: sqlite3.Row) -> None:
        """Validate that all required agent bio fields are not NULL."""
        validate_required_fields(row, AGENT_BIO_REQUIRED_FIELDS)

    def _row_to_agent_bio(self, row: sqlite3.Row) -> AgentBio:
        """Convert a database row to an AgentBio model."""
        return AgentBio(
            id=row["id"],
            agent_id=row["agent_id"],
            persona_bio=row["persona_bio"],
            persona_bio_source=PersonaBioSource(row["persona_bio_source"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def write_agent_bio(self, bio: AgentBio, *, conn: sqlite3.Connection) -> None:
        """Write an agent bio to SQLite.

        Raises:
            sqlite3.IntegrityError: If constraints are violated
            sqlite3.OperationalError: If database operation fails
        """
        row_values = tuple(
            bio.persona_bio_source.value
            if col == "persona_bio_source"
            else getattr(bio, col)
            for col in AGENT_BIO_COLUMNS
        )
        conn.execute(_INSERT_AGENT_BIO_SQL, row_values)

    def read_latest_agent_bio(
        self, agent_id: str, *, conn: sqlite3.Connection
    ) -> AgentBio | None:
        """Read the latest bio for an agent by created_at DESC."""
        validate_non_empty_string(agent_id, "agent_id")
        row = conn.execute(
            "SELECT * FROM agent_persona_bios WHERE agent_id = ? "
            "ORDER BY created_at DESC LIMIT 1",
            (agent_id,),
        ).fetchone()
        if row is None:
            return None
        self._validate_agent_bio_row(row)
        return self._row_to_agent_bio(row)

    def read_agent_bios_by_agent_id(
        self, agent_id: str, *, conn: sqlite3.Connection
    ) -> list[AgentBio]:
        """Read all bios for an agent, ordered by created_at DESC."""
        validate_non_empty_string(agent_id, "agent_id")
        rows = conn.execute(
            "SELECT * FROM agent_persona_bios WHERE agent_id = ? "
            "ORDER BY created_at DESC",
            (agent_id,),
        ).fetchall()
        result: list[AgentBio] = []
        for row in rows:
            self._validate_agent_bio_row(row)
            result.append(self._row_to_agent_bio(row))
        return result

    def read_latest_agent_bios_by_agent_ids(
        self, agent_ids: Iterable[str], *, conn: sqlite3.Connection
    ) -> dict[str, AgentBio | None]:
        """Read the latest bio per agent_id for the given agent IDs."""
        agent_ids_list = list(agent_ids)
        if not agent_ids_list:
            return {}
        q_marks = ",".join("?" for _ in agent_ids_list)
        sql = (
            "SELECT * FROM agent_persona_bios "
            f"WHERE agent_id IN ({q_marks}) "
            "ORDER BY agent_id, created_at DESC"
        )
        rows = conn.execute(sql, tuple(agent_ids_list)).fetchall()
        result: dict[str, AgentBio | None] = {}
        for row in rows:
            aid = row["agent_id"]
            if aid not in result:
                self._validate_agent_bio_row(row)
                result[aid] = self._row_to_agent_bio(row)
        for aid in agent_ids_list:
            if aid not in result:
                result[aid] = None
        return result

    def delete_agent_bios_by_agent_id(
        self, agent_id: str, *, conn: sqlite3.Connection
    ) -> None:
        """Delete all bios for an agent by agent_id."""
        validate_non_empty_string(agent_id, "agent_id")
        conn.execute("DELETE FROM agent_persona_bios WHERE agent_id = ?", (agent_id,))
