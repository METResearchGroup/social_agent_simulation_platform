"""SQLite implementation of agent liked post database adapter."""

from collections.abc import Iterable

from db.adapters.base import AgentLikedPostDatabaseAdapter
from db.adapters.sqlite.schema_utils import ordered_column_names
from db.schema import agent_liked_posts
from simulation.core.models.agent_liked_post import AgentLikedPost

AGENT_LIKED_POST_COLUMNS = ordered_column_names(agent_liked_posts)
_INSERT_SQL = (
    f"INSERT INTO agent_liked_posts ({', '.join(AGENT_LIKED_POST_COLUMNS)}) "
    f"VALUES ({', '.join('?' for _ in AGENT_LIKED_POST_COLUMNS)})"
)


class SQLiteAgentLikedPostAdapter(AgentLikedPostDatabaseAdapter):
    """SQLite implementation of AgentLikedPostDatabaseAdapter."""

    def write_agent_liked_posts(
        self, liked_posts: list[AgentLikedPost], *, conn: object
    ) -> None:
        """Write agent liked posts (batch)."""
        if not liked_posts:
            return
        import sqlite3

        c = conn
        assert isinstance(c, sqlite3.Connection)
        for lp in liked_posts:
            c.execute(_INSERT_SQL, (lp.agent_id, lp.post_uri))

    def read_agent_liked_posts_by_agent_ids(
        self, agent_ids: Iterable[str], *, conn: object
    ) -> dict[str, list[AgentLikedPost]]:
        """Read liked posts per agent_id."""
        import sqlite3

        c = conn
        assert isinstance(c, sqlite3.Connection)
        agent_ids_list = list(agent_ids)
        if not agent_ids_list:
            return {}
        q_marks = ",".join("?" for _ in agent_ids_list)
        sql = (
            "SELECT * FROM agent_liked_posts "
            f"WHERE agent_id IN ({q_marks}) "
            "ORDER BY agent_id, post_uri"
        )
        rows = c.execute(sql, tuple(agent_ids_list)).fetchall()
        result: dict[str, list[AgentLikedPost]] = {aid: [] for aid in agent_ids_list}
        for row in rows:
            lp = AgentLikedPost(agent_id=row["agent_id"], post_uri=row["post_uri"])
            result[row["agent_id"]].append(lp)
        return result
