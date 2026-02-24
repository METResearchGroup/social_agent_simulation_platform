"""SQLite implementation of agent linked agent database adapter."""

from collections.abc import Iterable

from db.adapters.base import AgentLinkedAgentDatabaseAdapter
from db.adapters.sqlite.schema_utils import ordered_column_names
from db.schema import agent_linked_agents
from simulation.core.models.agent_linked_agent import AgentLinkedAgent

AGENT_LINKED_AGENT_COLUMNS = ordered_column_names(agent_linked_agents)
_INSERT_SQL = (
    f"INSERT INTO agent_linked_agents ({', '.join(AGENT_LINKED_AGENT_COLUMNS)}) "
    f"VALUES ({', '.join('?' for _ in AGENT_LINKED_AGENT_COLUMNS)})"
)


class SQLiteAgentLinkedAgentAdapter(AgentLinkedAgentDatabaseAdapter):
    """SQLite implementation of AgentLinkedAgentDatabaseAdapter."""

    def write_agent_linked_agents(
        self, linked_agents: list[AgentLinkedAgent], *, conn: object
    ) -> None:
        """Write agent linked agents (batch)."""
        if not linked_agents:
            return
        import sqlite3

        c = conn
        assert isinstance(c, sqlite3.Connection)
        for la in linked_agents:
            c.execute(_INSERT_SQL, (la.agent_id, la.linked_agent_handle))

    def read_agent_linked_agents_by_agent_ids(
        self, agent_ids: Iterable[str], *, conn: object
    ) -> dict[str, list[AgentLinkedAgent]]:
        """Read linked agents per agent_id."""
        import sqlite3

        c = conn
        assert isinstance(c, sqlite3.Connection)
        agent_ids_list = list(agent_ids)
        if not agent_ids_list:
            return {}
        q_marks = ",".join("?" for _ in agent_ids_list)
        sql = (
            "SELECT * FROM agent_linked_agents "
            f"WHERE agent_id IN ({q_marks}) "
            "ORDER BY agent_id, linked_agent_handle"
        )
        rows = c.execute(sql, tuple(agent_ids_list)).fetchall()
        result: dict[str, list[AgentLinkedAgent]] = {aid: [] for aid in agent_ids_list}
        for row in rows:
            la = AgentLinkedAgent(
                agent_id=row["agent_id"],
                linked_agent_handle=row["linked_agent_handle"],
            )
            result[row["agent_id"]].append(la)
        return result
