"""SQLite implementation of run-agent snapshot persistence."""

import sqlite3
from collections.abc import Iterable

from db.adapters.base import RunAgentDatabaseAdapter
from db.adapters.sqlite.schema_utils import ordered_column_names, required_column_names
from db.adapters.sqlite.sqlite import validate_required_fields
from db.schema import run_agents as run_agents_table
from lib.validation_decorators import validate_inputs
from simulation.core.models.run_agents import RunAgentSnapshot
from simulation.core.utils.validators import validate_run_id

RUN_AGENT_COLUMNS = ordered_column_names(run_agents_table)
RUN_AGENT_REQUIRED_FIELDS = required_column_names(run_agents_table)
_INSERT_RUN_AGENT_SQL = (
    f"INSERT INTO run_agents ({', '.join(RUN_AGENT_COLUMNS)}) "
    f"VALUES ({', '.join('?' for _ in RUN_AGENT_COLUMNS)})"
)
_SELECT_RUN_AGENTS_FOR_RUN_SQL = (
    "SELECT * FROM run_agents WHERE run_id = ? ORDER BY selection_order ASC"
)


class SQLiteRunAgentAdapter(RunAgentDatabaseAdapter):
    """SQLite implementation of RunAgentDatabaseAdapter."""

    def _validate_run_agent_row(self, row: sqlite3.Row) -> None:
        validate_required_fields(row, RUN_AGENT_REQUIRED_FIELDS)

    def _row_to_run_agent_snapshot(self, row: sqlite3.Row) -> RunAgentSnapshot:
        return RunAgentSnapshot(
            run_id=row["run_id"],
            agent_id=row["agent_id"],
            selection_order=row["selection_order"],
            handle_at_start=row["handle_at_start"],
            display_name_at_start=row["display_name_at_start"],
            persona_bio_at_start=row["persona_bio_at_start"],
            followers_count_at_start=row["followers_count_at_start"],
            follows_count_at_start=row["follows_count_at_start"],
            posts_count_at_start=row["posts_count_at_start"],
            created_at=row["created_at"],
        )

    def write_run_agents(
        self,
        run_id: str,
        rows: Iterable[RunAgentSnapshot],
        *,
        conn: sqlite3.Connection,
    ) -> None:
        row_list = list(rows)
        if not row_list:
            return

        for row in row_list:
            if row.run_id != run_id:
                raise ValueError(
                    "All run agent snapshot rows must match the provided run_id"
                )

        conn.executemany(
            _INSERT_RUN_AGENT_SQL,
            [
                tuple(getattr(row, column) for column in RUN_AGENT_COLUMNS)
                for row in row_list
            ],
        )

    @validate_inputs((validate_run_id, "run_id"))
    def read_run_agents_for_run(
        self, run_id: str, *, conn: sqlite3.Connection
    ) -> list[RunAgentSnapshot]:
        rows = conn.execute(_SELECT_RUN_AGENTS_FOR_RUN_SQL, (run_id,)).fetchall()
        result: list[RunAgentSnapshot] = []
        for row in rows:
            self._validate_run_agent_row(row)
            result.append(self._row_to_run_agent_snapshot(row))
        return result
