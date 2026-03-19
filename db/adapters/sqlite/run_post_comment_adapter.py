"""SQLite implementation of immutable run-start comment snapshot persistence."""

import sqlite3
from collections.abc import Iterable

from db.adapters.base import RunPostCommentDatabaseAdapter
from db.adapters.sqlite.schema_utils import ordered_column_names
from db.schema import run_post_comments as run_post_comments_table
from lib.validation_decorators import validate_inputs
from simulation.core.models.run_post_comments import RunPostCommentSnapshot
from simulation.core.utils.validators import validate_run_id

RUN_POST_COMMENT_COLUMNS = ordered_column_names(run_post_comments_table)

_INSERT_RUN_POST_COMMENT_SQL = (
    f"INSERT INTO run_post_comments ({', '.join(RUN_POST_COMMENT_COLUMNS)}) "
    f"VALUES ({', '.join('?' for _ in RUN_POST_COMMENT_COLUMNS)})"
)


def _build_count_comments_by_run_posts_sql(num_ids: int) -> str:
    placeholders = ", ".join("?" for _ in range(num_ids))
    return (
        "SELECT run_post_id, COUNT(*) AS c "
        "FROM run_post_comments "
        "WHERE run_id = ? AND run_post_id IN ({placeholders}) "
        "GROUP BY run_post_id "
        "ORDER BY run_post_id ASC"
    ).format(placeholders=placeholders)


class SQLiteRunPostCommentAdapter(RunPostCommentDatabaseAdapter):
    """SQLite implementation of RunPostCommentDatabaseAdapter."""

    @staticmethod
    def _validate_run_post_comment_rows_match_run_id(
        rows: list[RunPostCommentSnapshot],
        *,
        run_id: str,
    ) -> None:
        if not rows:
            return
        if any(row.run_id != run_id for row in rows):
            raise ValueError(
                "All run post comment snapshot rows must match the provided run_id"
            )

    def write_run_post_comments(
        self,
        run_id: str,
        rows: Iterable[RunPostCommentSnapshot],
        *,
        conn: sqlite3.Connection,
    ) -> None:
        row_list = list(rows)
        self._validate_run_post_comment_rows_match_run_id(row_list, run_id=run_id)

        if not row_list:
            return

        conn.executemany(
            _INSERT_RUN_POST_COMMENT_SQL,
            [
                tuple(getattr(row, column) for column in RUN_POST_COMMENT_COLUMNS)
                for row in row_list
            ],
        )

    @validate_inputs((validate_run_id, "run_id"))
    def count_comments_by_run_post_ids(
        self,
        run_id: str,
        run_post_ids: Iterable[str],
        *,
        conn: sqlite3.Connection,
    ) -> dict[str, int]:
        run_post_ids_list = list(run_post_ids)
        if not run_post_ids_list:
            return {}

        sql = _build_count_comments_by_run_posts_sql(len(run_post_ids_list))
        params: tuple[object, ...] = (run_id, *run_post_ids_list)
        rows = conn.execute(sql, params).fetchall()

        result: dict[str, int] = {pid: 0 for pid in run_post_ids_list}
        for row in rows:
            result[str(row["run_post_id"])] = int(row["c"])
        return result
