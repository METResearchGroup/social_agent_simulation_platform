"""SQLite implementation of mutable seed-state agent-post comment persistence."""

import sqlite3
from collections.abc import Iterable

from db.adapters.base import AgentPostCommentDatabaseAdapter
from db.adapters.sqlite.schema_utils import ordered_column_names, required_column_names
from db.adapters.sqlite.sqlite import validate_required_fields
from db.schema import agent_post_comments as agent_post_comments_table
from simulation.core.models.agent_post_comments import AgentPostComment

AGENT_POST_COMMENT_COLUMNS = ordered_column_names(agent_post_comments_table)
AGENT_POST_COMMENT_REQUIRED_FIELDS = required_column_names(agent_post_comments_table)

_INSERT_AGENT_POST_COMMENT_SQL = (
    f"INSERT OR IGNORE INTO agent_post_comments ({', '.join(AGENT_POST_COMMENT_COLUMNS)}) "
    f"VALUES ({', '.join('?' for _ in AGENT_POST_COMMENT_COLUMNS)})"
)

_SELECT_COMMENTS_BY_AGENT_POST_IDS_SQL = (
    "SELECT * FROM agent_post_comments "
    "WHERE agent_post_id IN ({placeholders}) "
    "ORDER BY agent_post_id ASC, author_agent_id ASC, published_at ASC"
)


class SQLiteAgentPostCommentAdapter(AgentPostCommentDatabaseAdapter):
    """SQLite implementation of AgentPostCommentDatabaseAdapter."""

    def _validate_agent_post_comment_row(self, row: sqlite3.Row) -> None:
        validate_required_fields(row, AGENT_POST_COMMENT_REQUIRED_FIELDS)

    def _row_to_agent_post_comment(self, row: sqlite3.Row) -> AgentPostComment:
        return AgentPostComment(
            agent_post_comment_id=row["agent_post_comment_id"],
            agent_post_id=row["agent_post_id"],
            author_agent_id=row["author_agent_id"],
            body_text=row["body_text"],
            published_at=row["published_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def write_agent_post_comments(
        self,
        rows: Iterable[AgentPostComment],
        *,
        conn: sqlite3.Connection,
    ) -> None:
        row_list = list(rows)
        if not row_list:
            return

        conn.executemany(
            _INSERT_AGENT_POST_COMMENT_SQL,
            [
                tuple(getattr(row, column) for column in AGENT_POST_COMMENT_COLUMNS)
                for row in row_list
            ],
        )

    def list_comments_for_agent_post_ids(
        self,
        agent_post_ids: Iterable[str],
        *,
        conn: sqlite3.Connection,
    ) -> list[AgentPostComment]:
        agent_post_ids_list = list(agent_post_ids)
        agent_post_ids_list = [row_id for row_id in agent_post_ids_list if row_id]
        if not agent_post_ids_list:
            return []

        placeholders = ", ".join("?" for _ in agent_post_ids_list)
        sql = _SELECT_COMMENTS_BY_AGENT_POST_IDS_SQL.format(placeholders=placeholders)
        rows = conn.execute(sql, tuple(agent_post_ids_list)).fetchall()

        result: list[AgentPostComment] = []
        for row in rows:
            self._validate_agent_post_comment_row(row)
            result.append(self._row_to_agent_post_comment(row))
        return result
