"""SQLite implementation of agent database adapter."""

import sqlite3

from db.adapters.base import AgentDatabaseAdapter
from db.adapters.sqlite.schema_utils import ordered_column_names, required_column_names
from db.adapters.sqlite.sqlite import get_connection, validate_required_fields
from db.schema import agent as agent_table
from lib.validation_utils import validate_non_empty_string
from simulation.core.models.agent import Agent, PersonaSource

AGENT_COLUMNS = ordered_column_names(agent_table)
AGENT_REQUIRED_FIELDS = required_column_names(agent_table)
_INSERT_AGENT_SQL = (
    f"INSERT OR REPLACE INTO agent ({', '.join(AGENT_COLUMNS)}) "
    f"VALUES ({', '.join('?' for _ in AGENT_COLUMNS)})"
)


class SQLiteAgentAdapter(AgentDatabaseAdapter):
    """SQLite implementation of AgentDatabaseAdapter."""

    def _validate_agent_row(self, row: sqlite3.Row) -> None:
        """Validate that all required agent fields are not NULL."""
        validate_required_fields(row, AGENT_REQUIRED_FIELDS)

    def _row_to_agent(self, row: sqlite3.Row) -> Agent:
        """Convert a database row to an Agent model."""
        return Agent(
            agent_id=row["agent_id"],
            handle=row["handle"],
            persona_source=PersonaSource(row["persona_source"]),
            display_name=row["display_name"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def write_agent(self, agent: Agent, conn: sqlite3.Connection | None = None) -> None:
        """Write an agent to SQLite.

        When conn is provided, use it and do not commit; when None, use a new
        connection and commit.

        Raises:
            sqlite3.IntegrityError: If constraints are violated
            sqlite3.OperationalError: If database operation fails
        """
        row_values = tuple(
            agent.persona_source.value
            if col == "persona_source"
            else getattr(agent, col)
            for col in AGENT_COLUMNS
        )
        if conn is not None:
            conn.execute(_INSERT_AGENT_SQL, row_values)
        else:
            with get_connection() as c:
                c.execute(_INSERT_AGENT_SQL, row_values)
                c.commit()

    def read_agent(self, agent_id: str) -> Agent | None:
        """Read an agent by ID."""
        validate_non_empty_string(agent_id, "agent_id")
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM agent WHERE agent_id = ?", (agent_id,)
            ).fetchone()
            if row is None:
                return None
            self._validate_agent_row(row)
            return self._row_to_agent(row)

    def read_agent_by_handle(self, handle: str) -> Agent | None:
        """Read an agent by handle."""
        validate_non_empty_string(handle, "handle")
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM agent WHERE handle = ?", (handle,)
            ).fetchone()
            if row is None:
                return None
            self._validate_agent_row(row)
            return self._row_to_agent(row)

    def read_all_agents(self) -> list[Agent]:
        """Read all agents, ordered by handle for deterministic output."""
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM agent ORDER BY handle").fetchall()
            result: list[Agent] = []
            for row in rows:
                self._validate_agent_row(row)
                result.append(self._row_to_agent(row))
            return result
