"""SQLite implementation of immutable run-start like snapshot persistence."""

import sqlite3
from collections.abc import Iterable

from db.adapters.base import RunPostLikeDatabaseAdapter
from db.adapters.sqlite.schema_utils import ordered_column_names, required_column_names
from db.adapters.sqlite.sqlite import validate_required_fields
from db.schema import run_post_likes as run_post_likes_table
from lib.validation_decorators import validate_inputs
from simulation.core.models.run_post_likes import RunPostLikeSnapshot
from simulation.core.utils.validators import validate_run_id

RUN_POST_LIKE_COLUMNS = ordered_column_names(run_post_likes_table)
RUN_POST_LIKE_REQUIRED_FIELDS = required_column_names(run_post_likes_table)

_INSERT_RUN_POST_LIKE_SQL = (
    f"INSERT INTO run_post_likes ({', '.join(RUN_POST_LIKE_COLUMNS)}) "
    f"VALUES ({', '.join('?' for _ in RUN_POST_LIKE_COLUMNS)})"
)


def _build_count_likes_by_run_posts_sql(num_ids: int) -> str:
    placeholders = ", ".join("?" for _ in range(num_ids))
    return (
        "SELECT run_post_id, COUNT(*) AS c "
        "FROM run_post_likes "
        "WHERE run_id = ? AND run_post_id IN ({placeholders}) "
        "GROUP BY run_post_id "
        "ORDER BY run_post_id ASC"
    ).format(placeholders=placeholders)


class SQLiteRunPostLikeAdapter(RunPostLikeDatabaseAdapter):
    """SQLite implementation of RunPostLikeDatabaseAdapter."""

    def _validate_run_post_like_row(self, row: sqlite3.Row) -> None:
        validate_required_fields(row, RUN_POST_LIKE_REQUIRED_FIELDS)

    def _row_to_run_post_like_snapshot(self, row: sqlite3.Row) -> RunPostLikeSnapshot:
        return RunPostLikeSnapshot(
            run_post_like_id=row["run_post_like_id"],
            run_id=row["run_id"],
            run_post_id=row["run_post_id"],
            liker_agent_id=row["liker_agent_id"],
            liker_handle_at_start=row["liker_handle_at_start"],
            liker_display_name_at_start=row["liker_display_name_at_start"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _validate_run_post_like_rows_match_run_id(
        rows: list[RunPostLikeSnapshot],
        *,
        run_id: str,
    ) -> None:
        if not rows:
            return
        if any(row.run_id != run_id for row in rows):
            raise ValueError(
                "All run post like snapshot rows must match the provided run_id"
            )

    def write_run_post_likes(
        self,
        run_id: str,
        rows: Iterable[RunPostLikeSnapshot],
        *,
        conn: sqlite3.Connection,
    ) -> None:
        row_list = list(rows)
        self._validate_run_post_like_rows_match_run_id(row_list, run_id=run_id)

        if not row_list:
            return

        conn.executemany(
            _INSERT_RUN_POST_LIKE_SQL,
            [
                tuple(getattr(row, column) for column in RUN_POST_LIKE_COLUMNS)
                for row in row_list
            ],
        )

    @validate_inputs((validate_run_id, "run_id"))
    def count_likes_by_run_post_ids(
        self,
        run_id: str,
        run_post_ids: Iterable[str],
        *,
        conn: sqlite3.Connection,
    ) -> dict[str, int]:
        run_post_ids_list = list(run_post_ids)
        if not run_post_ids_list:
            return {}

        sql = _build_count_likes_by_run_posts_sql(len(run_post_ids_list))
        params: tuple[object, ...] = (run_id, *run_post_ids_list)
        rows = conn.execute(sql, params).fetchall()

        result: dict[str, int] = {pid: 0 for pid in run_post_ids_list}
        for row in rows:
            result[str(row["run_post_id"])] = int(row["c"])
        return result
