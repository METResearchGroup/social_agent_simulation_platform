"""SQLite implementation of run-follow-edge snapshot persistence."""

import sqlite3
from collections.abc import Iterable

from db.adapters.base import RunFollowEdgeDatabaseAdapter
from db.adapters.sqlite.schema_utils import ordered_column_names, required_column_names
from db.adapters.sqlite.sqlite import validate_required_fields
from db.schema import run_follow_edges as run_follow_edges_table
from lib.validation_decorators import validate_inputs
from simulation.core.models.run_follow_edges import RunFollowEdgeSnapshot
from simulation.core.utils.validators import validate_run_id

RUN_FOLLOW_EDGE_COLUMNS = ordered_column_names(run_follow_edges_table)
RUN_FOLLOW_EDGE_REQUIRED_FIELDS = required_column_names(run_follow_edges_table)
_INSERT_RUN_FOLLOW_EDGE_SQL = (
    f"INSERT INTO run_follow_edges ({', '.join(RUN_FOLLOW_EDGE_COLUMNS)}) "
    f"VALUES ({', '.join('?' for _ in RUN_FOLLOW_EDGE_COLUMNS)})"
)
_SELECT_RUN_FOLLOW_EDGES_FOR_RUN_SQL = (
    "SELECT * FROM run_follow_edges "
    "WHERE run_id = ? "
    "ORDER BY follower_agent_id ASC, target_agent_id ASC"
)


class SQLiteRunFollowEdgeAdapter(RunFollowEdgeDatabaseAdapter):
    """SQLite implementation of RunFollowEdgeDatabaseAdapter."""

    def _validate_run_follow_edge_row(self, row: sqlite3.Row) -> None:
        validate_required_fields(row, RUN_FOLLOW_EDGE_REQUIRED_FIELDS)

    def _row_to_run_follow_edge_snapshot(
        self, row: sqlite3.Row
    ) -> RunFollowEdgeSnapshot:
        return RunFollowEdgeSnapshot(
            run_id=row["run_id"],
            follower_agent_id=row["follower_agent_id"],
            target_agent_id=row["target_agent_id"],
            created_at=row["created_at"],
        )

    def write_run_follow_edges(
        self,
        run_id: str,
        rows: Iterable[RunFollowEdgeSnapshot],
        *,
        conn: sqlite3.Connection,
    ) -> None:
        row_list = list(rows)
        if not row_list:
            return

        for row in row_list:
            if row.run_id != run_id:
                raise ValueError(
                    "All run follow edge snapshot rows must match the provided run_id"
                )

        conn.executemany(
            _INSERT_RUN_FOLLOW_EDGE_SQL,
            [
                tuple(getattr(row, column) for column in RUN_FOLLOW_EDGE_COLUMNS)
                for row in row_list
            ],
        )

    @validate_inputs((validate_run_id, "run_id"))
    def read_run_follow_edges_for_run(
        self, run_id: str, *, conn: sqlite3.Connection
    ) -> list[RunFollowEdgeSnapshot]:
        rows = conn.execute(_SELECT_RUN_FOLLOW_EDGES_FOR_RUN_SQL, (run_id,)).fetchall()
        result: list[RunFollowEdgeSnapshot] = []
        for row in rows:
            self._validate_run_follow_edge_row(row)
            result.append(self._row_to_run_follow_edge_snapshot(row))
        return result
