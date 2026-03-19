"""SQLite implementation of run-post snapshot persistence."""

import sqlite3
from collections.abc import Iterable

from db.adapters.base import RunPostDatabaseAdapter
from db.adapters.sqlite.schema_utils import ordered_column_names, required_column_names
from db.adapters.sqlite.sqlite import validate_required_fields
from db.schema import run_posts as run_posts_table
from lib.validation_decorators import validate_inputs
from simulation.core.models.run_posts import RunPostSnapshot
from simulation.core.utils.validators import (
    validate_all_rows_match_run_id,
    validate_run_id,
)

RUN_POST_COLUMNS = ordered_column_names(run_posts_table)
RUN_POST_REQUIRED_FIELDS = required_column_names(run_posts_table)
_INSERT_RUN_POST_SQL = (
    f"INSERT INTO run_posts ({', '.join(RUN_POST_COLUMNS)}) "  # nosec B608
    f"VALUES ({', '.join('?' for _ in RUN_POST_COLUMNS)})"
)
_SELECT_RUN_POSTS_FOR_RUN_SQL = (
    "SELECT * FROM run_posts WHERE run_id = ? "
    "ORDER BY author_agent_id ASC, published_at_start ASC, run_post_id ASC"
)


def _build_read_run_posts_by_ids_sql(num_ids: int) -> str:
    placeholders = ", ".join("?" for _ in range(num_ids))
    return (
        f"SELECT * FROM run_posts WHERE run_id = ? AND run_post_id IN ({placeholders})"  # nosec B608
    )


class SQLiteRunPostAdapter(RunPostDatabaseAdapter):
    """SQLite implementation of RunPostDatabaseAdapter."""

    def _validate_run_post_row(self, row: sqlite3.Row) -> None:
        validate_required_fields(row, RUN_POST_REQUIRED_FIELDS)

    def _row_to_run_post_snapshot(self, row: sqlite3.Row) -> RunPostSnapshot:
        return RunPostSnapshot(
            run_post_id=row["run_post_id"],
            run_id=row["run_id"],
            agent_post_id=row["agent_post_id"],
            author_agent_id=row["author_agent_id"],
            author_handle_at_start=row["author_handle_at_start"],
            author_display_name_at_start=row["author_display_name_at_start"],
            body_text_at_start=row["body_text_at_start"],
            published_at_start=row["published_at_start"],
            source_post_id_at_start=row["source_post_id_at_start"],
            source_at_start=row["source_at_start"],
            source_uri_at_start=row["source_uri_at_start"],
            created_at=row["created_at"],
        )

    def write_run_posts(
        self,
        run_id: str,
        rows: Iterable[RunPostSnapshot],
        *,
        conn: sqlite3.Connection,
    ) -> None:
        row_list = list(rows)
        self._validate_run_posts(row_list, run_id)

        conn.executemany(
            _INSERT_RUN_POST_SQL,
            [
                tuple(getattr(row, column) for column in RUN_POST_COLUMNS)
                for row in row_list
            ],
        )

    @validate_inputs((validate_run_id, "run_id"))
    def read_run_posts_for_run(
        self, run_id: str, *, conn: sqlite3.Connection
    ) -> list[RunPostSnapshot]:
        rows = conn.execute(_SELECT_RUN_POSTS_FOR_RUN_SQL, (run_id,)).fetchall()
        result: list[RunPostSnapshot] = []
        for row in rows:
            self._validate_run_post_row(row)
            result.append(self._row_to_run_post_snapshot(row))
        return result

    @validate_inputs((validate_run_id, "run_id"))
    def read_run_posts_by_ids(
        self,
        run_id: str,
        post_ids: Iterable[str],
        *,
        conn: sqlite3.Connection,
    ) -> list[RunPostSnapshot]:
        post_ids_list = list(post_ids)
        if not post_ids_list:
            return []
        sql = _build_read_run_posts_by_ids_sql(len(post_ids_list))
        params: tuple[object, ...] = (run_id, *post_ids_list)
        rows = conn.execute(sql, params).fetchall()
        row_by_id = {row["run_post_id"]: row for row in rows}
        result: list[RunPostSnapshot] = []
        for pid in post_ids_list:
            if pid in row_by_id:
                row = row_by_id[pid]
                self._validate_run_post_row(row)
                result.append(self._row_to_run_post_snapshot(row))
        return result

    def _validate_run_posts(self, row_list: list[RunPostSnapshot], run_id: str) -> None:
        """Validate run post snapshot rows."""
        if not row_list:
            return

        validate_all_rows_match_run_id(
            row_list,
            run_id,
            message="All run post snapshot rows must match the provided run_id",
        )
