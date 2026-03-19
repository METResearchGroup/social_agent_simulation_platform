"""SQLite implementation of mutable seed-state agent-post like persistence."""

import sqlite3
from collections.abc import Iterable

from db.adapters.base import AgentPostLikeDatabaseAdapter
from db.adapters.sqlite.schema_utils import ordered_column_names, required_column_names
from db.adapters.sqlite.sqlite import validate_required_fields
from db.schema import agent_post_likes as agent_post_likes_table
from simulation.core.models.agent_post_likes import AgentPostLike

AGENT_POST_LIKE_COLUMNS = ordered_column_names(agent_post_likes_table)
AGENT_POST_LIKE_REQUIRED_FIELDS = required_column_names(agent_post_likes_table)

_INSERT_AGENT_POST_LIKE_SQL = (
    f"INSERT OR IGNORE INTO agent_post_likes ({', '.join(AGENT_POST_LIKE_COLUMNS)}) "
    f"VALUES ({', '.join('?' for _ in AGENT_POST_LIKE_COLUMNS)})"
)

_SELECT_LIKES_BY_AGENT_POST_IDS_SQL = (
    "SELECT * FROM agent_post_likes "
    "WHERE agent_post_id IN ({placeholders}) "
    "ORDER BY agent_post_id ASC, liker_agent_id ASC"
)


class SQLiteAgentPostLikeAdapter(AgentPostLikeDatabaseAdapter):
    """SQLite implementation of AgentPostLikeDatabaseAdapter."""

    def _validate_agent_post_like_row(self, row: sqlite3.Row) -> None:
        validate_required_fields(row, AGENT_POST_LIKE_REQUIRED_FIELDS)

    def _row_to_agent_post_like(self, row: sqlite3.Row) -> AgentPostLike:
        return AgentPostLike(
            agent_post_like_id=row["agent_post_like_id"],
            agent_post_id=row["agent_post_id"],
            liker_agent_id=row["liker_agent_id"],
            created_at=row["created_at"],
        )

    def write_agent_post_likes(
        self,
        rows: Iterable[AgentPostLike],
        *,
        conn: sqlite3.Connection,
    ) -> None:
        row_list = list(rows)
        if not row_list:
            return

        conn.executemany(
            _INSERT_AGENT_POST_LIKE_SQL,
            [
                tuple(getattr(row, column) for column in AGENT_POST_LIKE_COLUMNS)
                for row in row_list
            ],
        )

    def list_likes_for_agent_post_ids(
        self,
        agent_post_ids: Iterable[str],
        *,
        conn: sqlite3.Connection,
    ) -> list[AgentPostLike]:
        agent_post_ids_list = list(agent_post_ids)
        agent_post_ids_list = [row_id for row_id in agent_post_ids_list if row_id]
        if not agent_post_ids_list:
            return []

        placeholders = ", ".join("?" for _ in agent_post_ids_list)
        sql = _SELECT_LIKES_BY_AGENT_POST_IDS_SQL.format(placeholders=placeholders)
        rows = conn.execute(sql, tuple(agent_post_ids_list)).fetchall()

        result: list[AgentPostLike] = []
        for row in rows:
            self._validate_agent_post_like_row(row)
            result.append(self._row_to_agent_post_like(row))
        return result
