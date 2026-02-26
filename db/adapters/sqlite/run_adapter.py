"""SQLite implementation of run database adapter."""

from __future__ import annotations

import json
import sqlite3

from db.adapters.base import RunDatabaseAdapter
from db.adapters.sqlite.schema_utils import required_column_names
from db.adapters.sqlite.sqlite import validate_required_fields
from db.schema import runs
from lib.validation_decorators import validate_inputs
from simulation.core.metrics.defaults import get_default_metric_keys
from simulation.core.models.actions import TurnAction
from simulation.core.models.runs import Run, RunStatus
from simulation.core.models.turns import TurnMetadata
from simulation.core.utils.exceptions import (
    DuplicateTurnMetadataError,
    RunNotFoundError,
)
from simulation.core.utils.validators import validate_run_id, validate_turn_number

TURN_METADATA_REQUIRED_COLS = ["run_id", "turn_number", "total_actions", "created_at"]


def _validate_turn_metadata_row(row: sqlite3.Row) -> None:
    """Validate that row has required columns and no NULLs. Raises KeyError or ValueError."""
    for col in TURN_METADATA_REQUIRED_COLS:
        if col not in row.keys():
            raise KeyError(f"Missing required column '{col}' in turn_metadata row")
    for col in TURN_METADATA_REQUIRED_COLS:
        if row[col] is None:
            raise ValueError(f"Turn metadata has NULL fields: {col}={row[col]}")


def _parse_total_actions_from_row(row: sqlite3.Row) -> dict[TurnAction, int]:
    """Parse total_actions JSON and convert string keys to TurnAction. Raises ValueError."""
    try:
        total_actions_dict = json.loads(row["total_actions"])
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Could not parse total_actions as JSON for turn_metadata: {e}"
        ) from e
    try:
        return {TurnAction(k): v for k, v in total_actions_dict.items()}
    except (ValueError, KeyError) as e:
        valid_keys = [action.value for action in TurnAction]
        raise ValueError(
            f"Invalid action type in total_actions for turn_metadata: {e}. "
            f"Expected keys: {valid_keys}, got: {list(total_actions_dict.keys())}"
        ) from e


class SQLiteRunAdapter(RunDatabaseAdapter):
    """SQLite implementation of RunDatabaseAdapter.

    This implementation raises SQLite-specific exceptions. See method docstrings
    for details on specific exception types.
    """

    def _row_to_run(self, row: sqlite3.Row) -> Run:
        """Convert a database row to a Run model.

        Args:
            row: SQLite Row object containing run data

        Returns:
            Run model instance

        Raises:
            ValueError: If required fields are NULL or status is invalid
            KeyError: If required columns are missing from row
        """
        validate_required_fields(row, required_column_names(runs))

        # Convert status string to RunStatus enum, handling invalid values
        try:
            status = RunStatus(row["status"])
        except ValueError as err:
            raise ValueError(
                f"Invalid status value: {row['status']}. Must be one of: {[s.value for s in RunStatus]}"
            ) from err

        app_user_id = row["app_user_id"] if "app_user_id" in row.keys() else None

        metric_keys: list[str]
        raw_metric_keys: str | None = (
            row["metric_keys"] if "metric_keys" in row.keys() else None
        )
        if raw_metric_keys is None or (
            isinstance(raw_metric_keys, str) and not raw_metric_keys.strip()
        ):
            metric_keys = get_default_metric_keys()
        else:
            parsed = json.loads(raw_metric_keys)
            if not isinstance(parsed, list):
                raise ValueError(
                    f"metric_keys must be a JSON array, got {type(parsed).__name__}"
                )
            for i, k in enumerate(parsed):
                if not isinstance(k, str):
                    raise ValueError(
                        f"metric_keys[{i}] must be a string, got {type(k).__name__}: {k!r}"
                    )
            metric_keys = sorted(parsed)

        return Run(
            run_id=row["run_id"],
            app_user_id=app_user_id,
            created_at=row["created_at"],
            total_turns=row["total_turns"],
            total_agents=row["total_agents"],
            feed_algorithm=row["feed_algorithm"],
            metric_keys=metric_keys,
            started_at=row["started_at"],
            status=status,
            completed_at=row["completed_at"],
        )

    def write_run(self, run: Run, *, conn: sqlite3.Connection) -> None:
        """Write a run to SQLite.

        Raises:
            sqlite3.IntegrityError: If run_id violates constraints
            sqlite3.OperationalError: If database operation fails
        """
        metric_keys_json: str = json.dumps(sorted(run.metric_keys))

        conn.execute(
            """
            INSERT OR REPLACE INTO runs 
            (run_id, app_user_id, created_at, total_turns, total_agents, feed_algorithm, metric_keys, started_at, status, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                run.run_id,
                run.app_user_id,
                run.created_at,
                run.total_turns,
                run.total_agents,
                run.feed_algorithm,
                metric_keys_json,
                run.started_at,
                run.status.value,  # Convert enum to string explicitly
                run.completed_at,
            ),
        )

    def read_run(self, run_id: str, *, conn: sqlite3.Connection) -> Run | None:
        """Read a run from SQLite.

        Raises:
            ValueError: If the run data is invalid (NULL fields, invalid status)
            sqlite3.OperationalError: If database operation fails
            KeyError: If required columns are missing from the database row
        """
        row = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()

        if row is None:
            return None

        return self._row_to_run(row)

    def read_all_runs(self, *, conn: sqlite3.Connection) -> list[Run]:
        """Read all runs from SQLite.

        Raises:
            ValueError: If any run data is invalid (NULL fields, invalid status)
            sqlite3.OperationalError: If database operation fails
            KeyError: If required columns are missing from any database row
        """
        rows = conn.execute("SELECT * FROM runs ORDER BY created_at DESC").fetchall()

        return [self._row_to_run(row) for row in rows]

    def update_run_status(
        self,
        run_id: str,
        status: str,
        *,
        completed_at: str | None = None,
        conn: sqlite3.Connection,
    ) -> None:
        """Update run status in SQLite.

        Raises:
            RunNotFoundError: If no run exists with the given run_id
            sqlite3.OperationalError: If database operation fails
            sqlite3.IntegrityError: If status value violates CHECK constraints
        """
        cursor = conn.execute(
            """
            UPDATE runs
            SET status = ?, completed_at = ?
            WHERE run_id = ?
            """,
            (status, completed_at, run_id),
        )
        if cursor.rowcount == 0:
            raise RunNotFoundError(run_id)

    @validate_inputs((validate_run_id, "run_id"), (validate_turn_number, "turn_number"))
    def read_turn_metadata(
        self,
        run_id: str,
        turn_number: int,
        *,
        conn: sqlite3.Connection,
    ) -> TurnMetadata | None:
        """Read turn metadata from SQLite.

        The total_actions field is stored as JSON with string keys (e.g., {"like": 5}).
        This method converts those string keys to TurnAction enum keys.

        Args:
            run_id: The ID of the run
            turn_number: The turn number (0-indexed)
            conn: Connection.

        Returns:
            TurnMetadata if found, None otherwise

        Raises:
            ValueError: If run_id is invalid or turn_number is invalid
            ValueError: If the turn metadata data is invalid (NULL fields, invalid action types)
            sqlite3.OperationalError: If database operation fails
            KeyError: If required columns are missing from the database row
        """
        row = conn.execute(
            "SELECT * FROM turn_metadata WHERE run_id = ? AND turn_number = ?",
            (run_id, turn_number),
        ).fetchone()

        if row is None:
            return None

        _validate_turn_metadata_row(row)
        total_actions = _parse_total_actions_from_row(row)
        try:
            return TurnMetadata(
                run_id=row["run_id"],
                turn_number=row["turn_number"],
                total_actions=total_actions,
                created_at=row["created_at"],
            )
        except Exception as e:
            raise ValueError(
                f"Invalid turn metadata data: {e}. "
                f"run_id={row['run_id']}, turn_number={row['turn_number']}, "
                f"total_actions={total_actions}, created_at={row['created_at']}"
            ) from e

    @validate_inputs((validate_run_id, "run_id"))
    def read_turn_metadata_for_run(
        self, run_id: str, *, conn: sqlite3.Connection
    ) -> list[TurnMetadata]:
        """Read all turn metadata rows for a run from SQLite.

        Args:
            run_id: The ID of the run
            conn: Connection.

        Returns:
            List of TurnMetadata ordered by turn_number ascending.
            Returns empty list if no metadata exists for the run.

        Raises:
            ValueError: If run_id is invalid or row data is invalid
            sqlite3.OperationalError: If database operation fails
            KeyError: If required columns are missing from a database row
        """
        rows = conn.execute(
            "SELECT * FROM turn_metadata WHERE run_id = ? ORDER BY turn_number ASC",
            (run_id,),
        ).fetchall()

        turn_metadata_list: list[TurnMetadata] = []
        for row in rows:
            _validate_turn_metadata_row(row)
            total_actions = _parse_total_actions_from_row(row)
            try:
                turn_metadata_list.append(
                    TurnMetadata(
                        run_id=row["run_id"],
                        turn_number=row["turn_number"],
                        total_actions=total_actions,
                        created_at=row["created_at"],
                    )
                )
            except Exception as e:
                raise ValueError(
                    f"Invalid turn metadata data: {e}. "
                    f"run_id={row['run_id']}, turn_number={row['turn_number']}, "
                    f"total_actions={total_actions}, created_at={row['created_at']}"
                ) from e

        return turn_metadata_list

    def write_turn_metadata(
        self,
        turn_metadata: TurnMetadata,
        *,
        conn: sqlite3.Connection,
    ) -> None:
        """Write turn metadata to SQLite.

        Writes to the `turn_metadata` table. Uses INSERT.

        Args:
            turn_metadata: TurnMetadata model to write
            conn: Connection.

        Raises:
            sqlite3.OperationalError: If database operation fails
            DuplicateTurnMetadataError: If turn metadata already exists
        """
        existing_turn_metadata = self.read_turn_metadata(
            turn_metadata.run_id,
            turn_metadata.turn_number,
            conn=conn,
        )

        if existing_turn_metadata is not None:
            raise DuplicateTurnMetadataError(
                turn_metadata.run_id, turn_metadata.turn_number
            )

        total_actions_json = json.dumps(
            {k.value: v for k, v in turn_metadata.total_actions.items()}
        )

        try:
            conn.execute(
                "INSERT INTO turn_metadata (run_id, turn_number, total_actions, created_at) VALUES (?, ?, ?, ?)",
                (
                    turn_metadata.run_id,
                    turn_metadata.turn_number,
                    total_actions_json,
                    turn_metadata.created_at,
                ),
            )
        except sqlite3.IntegrityError:
            raise DuplicateTurnMetadataError(
                turn_metadata.run_id, turn_metadata.turn_number
            )
