"""SQLite implementation of editable seed-state agent post persistence."""

import sqlite3
from collections.abc import Iterable

from db.adapters.base import AgentPostDatabaseAdapter
from db.adapters.sqlite.schema_utils import ordered_column_names, required_column_names
from db.adapters.sqlite.sqlite import validate_required_fields
from db.schema import agent_posts as agent_posts_table
from lib.validation_utils import validate_non_empty_string
from simulation.core.models.agent_posts import AgentPost
from simulation.core.utils.validators import validate_agent_id

AGENT_POST_COLUMNS = ordered_column_names(agent_posts_table)
AGENT_POST_REQUIRED_FIELDS = required_column_names(agent_posts_table)
_INSERT_AGENT_POST_SQL = (
    f"INSERT OR REPLACE INTO agent_posts ({', '.join(AGENT_POST_COLUMNS)}) "
    f"VALUES ({', '.join('?' for _ in AGENT_POST_COLUMNS)})"
)
_UPSERT_IMPORTED_AGENT_POST_SQL = (
    f"INSERT INTO agent_posts ({', '.join(AGENT_POST_COLUMNS)}) "
    f"VALUES ({', '.join('?' for _ in AGENT_POST_COLUMNS)}) "
    "ON CONFLICT(source, source_post_id) DO UPDATE SET "
    "agent_id = excluded.agent_id, "
    "body_text = excluded.body_text, "
    "published_at = excluded.published_at, "
    "updated_at = excluded.updated_at, "
    "source_uri = excluded.source_uri, "
    "imported_author_handle = excluded.imported_author_handle, "
    "imported_author_display_name = excluded.imported_author_display_name, "
    "import_metadata_json = excluded.import_metadata_json "
    "WHERE "
    "agent_posts.agent_id != excluded.agent_id "
    "OR agent_posts.body_text != excluded.body_text "
    "OR agent_posts.published_at != excluded.published_at "
    "OR agent_posts.source_uri IS NOT excluded.source_uri "
    "OR agent_posts.imported_author_handle IS NOT excluded.imported_author_handle "
    "OR agent_posts.imported_author_display_name IS NOT excluded.imported_author_display_name "
    "OR agent_posts.import_metadata_json IS NOT excluded.import_metadata_json"
)


class SQLiteAgentPostAdapter(AgentPostDatabaseAdapter):
    """SQLite implementation of AgentPostDatabaseAdapter."""

    def _validate_agent_post_row(self, row: sqlite3.Row) -> None:
        validate_required_fields(row, AGENT_POST_REQUIRED_FIELDS)

    def _row_to_agent_post(self, row: sqlite3.Row) -> AgentPost:
        return AgentPost(
            agent_post_id=row["agent_post_id"],
            agent_id=row["agent_id"],
            body_text=row["body_text"],
            published_at=row["published_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            source_post_id=row["source_post_id"],
            source=row["source"],
            source_uri=row["source_uri"],
            imported_author_handle=row["imported_author_handle"],
            imported_author_display_name=row["imported_author_display_name"],
            import_metadata_json=row["import_metadata_json"],
        )

    def write_agent_posts(
        self,
        posts: Iterable[AgentPost],
        *,
        conn: sqlite3.Connection,
    ) -> None:
        post_list = list(posts)
        if not post_list:
            return
        conn.executemany(
            _INSERT_AGENT_POST_SQL,
            [
                tuple(getattr(post, column) for column in AGENT_POST_COLUMNS)
                for post in post_list
            ],
        )

    def upsert_imported_agent_posts(
        self,
        posts: Iterable[AgentPost],
        *,
        conn: sqlite3.Connection,
    ) -> None:
        post_list = list(posts)
        if not post_list:
            return

        for post in post_list:
            validate_agent_id(post.agent_id)
            if post.source_post_id is None:
                raise ValueError(
                    "Imported agent posts must provide source_post_id for idempotent upsert"
                )
            if post.source is None:
                raise ValueError(
                    "Imported agent posts must provide source for idempotent upsert"
                )
            validate_non_empty_string(post.source_post_id)
            validate_non_empty_string(post.source)

        conn.executemany(
            _UPSERT_IMPORTED_AGENT_POST_SQL,
            [
                tuple(getattr(post, column) for column in AGENT_POST_COLUMNS)
                for post in post_list
            ],
        )

    def read_posts_for_agent_ids(
        self,
        agent_ids: Iterable[str],
        *,
        conn: sqlite3.Connection,
    ) -> list[AgentPost]:
        agent_id_list = [validate_agent_id(agent_id) for agent_id in agent_ids]
        if not agent_id_list:
            return []

        placeholders = ", ".join("?" for _ in agent_id_list)
        sql = (
            f"SELECT * FROM agent_posts WHERE agent_id IN ({placeholders}) "
            "ORDER BY agent_id ASC, published_at ASC, agent_post_id ASC"
        )
        rows = conn.execute(sql, tuple(agent_id_list)).fetchall()
        result: list[AgentPost] = []
        for row in rows:
            self._validate_agent_post_row(row)
            result.append(self._row_to_agent_post(row))
        return result

    def count_posts_by_agent_ids(
        self,
        agent_ids: Iterable[str],
        *,
        conn: sqlite3.Connection,
    ) -> dict[str, int]:
        agent_id_list = [validate_agent_id(agent_id) for agent_id in agent_ids]
        if not agent_id_list:
            return {}

        placeholders = ", ".join("?" for _ in agent_id_list)
        sql = (
            f"SELECT agent_id, COUNT(*) AS c FROM agent_posts "
            f"WHERE agent_id IN ({placeholders}) "
            "GROUP BY agent_id "
            "ORDER BY agent_id ASC"
        )
        rows = conn.execute(sql, tuple(agent_id_list)).fetchall()
        result: dict[str, int] = {agent_id: 0 for agent_id in agent_id_list}
        for row in rows:
            result[str(row["agent_id"])] = int(row["c"])
        return result

    def count_all_posts(self, *, conn: sqlite3.Connection) -> int:
        row = conn.execute("SELECT COUNT(*) FROM agent_posts").fetchone()
        return int(row[0]) if row is not None else 0
