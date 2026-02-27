"""SQLite implementation of agent database adapter."""

import sqlite3

from db.adapters.base import AgentDatabaseAdapter
from db.adapters.sqlite.schema_utils import ordered_column_names, required_column_names
from db.adapters.sqlite.sqlite import validate_required_fields
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

    def _map_rows_to_agents(self, rows: list[sqlite3.Row]) -> list[Agent]:
        result: list[Agent] = []
        for row in rows:
            self._validate_agent_row(row)
            result.append(self._row_to_agent(row))
        return result

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

    def write_agent(self, agent: Agent, *, conn: sqlite3.Connection) -> None:
        """Write an agent to SQLite.

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
        conn.execute(_INSERT_AGENT_SQL, row_values)

    def read_agent(self, agent_id: str, *, conn: sqlite3.Connection) -> Agent | None:
        """Read an agent by ID."""
        validate_non_empty_string(agent_id, "agent_id")
        row = conn.execute(
            "SELECT * FROM agent WHERE agent_id = ?", (agent_id,)
        ).fetchone()
        if row is None:
            return None
        self._validate_agent_row(row)
        return self._row_to_agent(row)

    def read_agent_by_handle(
        self, handle: str, *, conn: sqlite3.Connection
    ) -> Agent | None:
        """Read an agent by handle."""
        validate_non_empty_string(handle, "handle")
        row = conn.execute("SELECT * FROM agent WHERE handle = ?", (handle,)).fetchone()
        if row is None:
            return None
        self._validate_agent_row(row)
        return self._row_to_agent(row)

    def read_all_agents(self, *, conn: sqlite3.Connection) -> list[Agent]:
        """Read all agents, ordered by updated_at DESC, handle ASC for determinism."""
        rows = conn.execute(
            "SELECT * FROM agent ORDER BY updated_at DESC, handle ASC"
        ).fetchall()
        return self._map_rows_to_agents(rows)

    def read_agents_page(
        self, *, limit: int, offset: int, conn: sqlite3.Connection
    ) -> list[Agent]:
        """Read a page of agents, ordered by updated_at DESC, handle ASC."""
        rows = conn.execute(
            "SELECT * FROM agent ORDER BY updated_at DESC, handle ASC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return self._map_rows_to_agents(rows)

    def read_agents_page_by_handle_like(
        self,
        *,
        handle_like: str,
        limit: int,
        offset: int,
        conn: sqlite3.Connection,
    ) -> list[Agent]:
        """Read a page of agents filtered by handle LIKE, ordered by updated_at DESC, handle ASC."""
        rows = conn.execute(
            (
                "SELECT * FROM agent "
                "WHERE handle LIKE ? ESCAPE '\\' COLLATE NOCASE "
                "ORDER BY updated_at DESC, handle ASC LIMIT ? OFFSET ?"
            ),
            (handle_like, limit, offset),
        ).fetchall()
        return self._map_rows_to_agents(rows)

    def delete_agent(self, agent_id: str, *, conn: sqlite3.Connection) -> None:
        """Delete an agent by agent_id."""
        validate_non_empty_string(agent_id, "agent_id")
        conn.execute("DELETE FROM agent WHERE agent_id = ?", (agent_id,))
