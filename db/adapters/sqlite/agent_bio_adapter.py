"""SQLite implementation of agent persona bio database adapter."""

import sqlite3

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

        conn is required; repository must provide it (from its transaction).

        Raises:
            sqlite3.IntegrityError: If constraints are violated
            sqlite3.OperationalError: If database operation fails
        """
        if conn is None:
            raise ValueError("conn is required; repository must provide it")
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
        if conn is None:
            raise ValueError("conn is required; repository must provide it")
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
        if conn is None:
            raise ValueError("conn is required; repository must provide it")
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
