"""SQLite implementation of agent profile comment database adapter."""

from collections.abc import Iterable

from db.adapters.base import AgentProfileCommentDatabaseAdapter
from db.adapters.sqlite.schema_utils import ordered_column_names
from db.schema import agent_profile_comments
from simulation.core.models.agent_profile_comment import AgentProfileComment

AGENT_PROFILE_COMMENT_COLUMNS = ordered_column_names(agent_profile_comments)
_INSERT_SQL = (
    f"INSERT INTO agent_profile_comments ({', '.join(AGENT_PROFILE_COMMENT_COLUMNS)}) "
    f"VALUES ({', '.join('?' for _ in AGENT_PROFILE_COMMENT_COLUMNS)})"
)


class SQLiteAgentProfileCommentAdapter(AgentProfileCommentDatabaseAdapter):
    """SQLite implementation of AgentProfileCommentDatabaseAdapter."""

    def write_agent_profile_comments(
        self, comments: list[AgentProfileComment], *, conn: object
    ) -> None:
        """Write agent profile comments (batch)."""
        if not comments:
            return
        import sqlite3

        c = conn
        assert isinstance(c, sqlite3.Connection)
        for comment in comments:
            row = (
                comment.id,
                comment.agent_id,
                comment.post_uri,
                comment.text,
                comment.created_at,
                comment.updated_at,
            )
            c.execute(_INSERT_SQL, row)

    def read_agent_profile_comments_by_agent_ids(
        self, agent_ids: Iterable[str], *, conn: object
    ) -> dict[str, list[AgentProfileComment]]:
        """Read comments per agent_id."""
        import sqlite3

        c = conn
        assert isinstance(c, sqlite3.Connection)
        agent_ids_list = list(agent_ids)
        if not agent_ids_list:
            return {}
        q_marks = ",".join("?" for _ in agent_ids_list)
        sql = (
            "SELECT * FROM agent_profile_comments "
            f"WHERE agent_id IN ({q_marks}) "
            "ORDER BY agent_id, created_at"
        )
        rows = c.execute(sql, tuple(agent_ids_list)).fetchall()
        result: dict[str, list[AgentProfileComment]] = {
            aid: [] for aid in agent_ids_list
        }
        for row in rows:
            comment = AgentProfileComment(
                id=row["id"],
                agent_id=row["agent_id"],
                post_uri=row["post_uri"],
                text=row["text"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            result[row["agent_id"]].append(comment)
        return result
