"""SQLite implementation of metrics database adapter."""

from __future__ import annotations

import json
import sqlite3
from typing import cast

from db.adapters.base import MetricsDatabaseAdapter
from db.adapters.sqlite.sqlite import get_connection
from lib.validation_decorators import validate_inputs
from simulation.core.models.metrics import ComputedMetrics, RunMetrics, TurnMetrics
from simulation.core.validators import validate_run_id, validate_turn_number

TURN_METRICS_REQUIRED_COLS: list[str] = [
    "run_id",
    "turn_number",
    "metrics",
    "created_at",
]
RUN_METRICS_REQUIRED_COLS: list[str] = ["run_id", "metrics", "created_at"]


def _validate_required_cols(*, row: sqlite3.Row, required_cols: list[str]) -> None:
    for col in required_cols:
        if col not in row.keys():
            raise KeyError(f"Missing required column '{col}'")
        if row[col] is None:
            raise ValueError(f"Unexpected NULL for required column '{col}'")


def _parse_metrics_json(*, raw: str) -> ComputedMetrics:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Could not parse metrics as JSON: {e}") from e
    if not isinstance(parsed, dict):
        raise ValueError("metrics must be a JSON object")
    return cast(ComputedMetrics, parsed)


class SQLiteMetricsAdapter(MetricsDatabaseAdapter):
    def write_turn_metrics(
        self,
        turn_metrics: TurnMetrics,
        conn: sqlite3.Connection | None = None,
    ) -> None:
        if conn is None:
            raise ValueError("conn is required; repository must provide it")
        metrics_json = json.dumps(turn_metrics.metrics)
        conn.execute(
            """
            INSERT OR REPLACE INTO turn_metrics
            (run_id, turn_number, metrics, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                turn_metrics.run_id,
                turn_metrics.turn_number,
                metrics_json,
                turn_metrics.created_at,
            ),
        )

    @validate_inputs((validate_run_id, "run_id"), (validate_turn_number, "turn_number"))
    def read_turn_metrics(self, run_id: str, turn_number: int) -> TurnMetrics | None:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM turn_metrics WHERE run_id = ? AND turn_number = ?",
                (run_id, turn_number),
            ).fetchone()

        if row is None:
            return None

        _validate_required_cols(row=row, required_cols=TURN_METRICS_REQUIRED_COLS)
        metrics = _parse_metrics_json(raw=row["metrics"])
        return TurnMetrics(
            run_id=row["run_id"],
            turn_number=row["turn_number"],
            metrics=metrics,
            created_at=row["created_at"],
        )

    @validate_inputs((validate_run_id, "run_id"))
    def read_turn_metrics_for_run(self, run_id: str) -> list[TurnMetrics]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM turn_metrics WHERE run_id = ? ORDER BY turn_number ASC",
                (run_id,),
            ).fetchall()

        result: list[TurnMetrics] = []
        for row in rows:
            _validate_required_cols(row=row, required_cols=TURN_METRICS_REQUIRED_COLS)
            metrics = _parse_metrics_json(raw=row["metrics"])
            result.append(
                TurnMetrics(
                    run_id=row["run_id"],
                    turn_number=row["turn_number"],
                    metrics=metrics,
                    created_at=row["created_at"],
                )
            )
        return result

    def write_run_metrics(
        self,
        run_metrics: RunMetrics,
        conn: sqlite3.Connection | None = None,
    ) -> None:
        if conn is None:
            raise ValueError("conn is required; repository must provide it")
        metrics_json = json.dumps(run_metrics.metrics)
        conn.execute(
            """
            INSERT OR REPLACE INTO run_metrics
            (run_id, metrics, created_at)
            VALUES (?, ?, ?)
            """,
            (run_metrics.run_id, metrics_json, run_metrics.created_at),
        )

    @validate_inputs((validate_run_id, "run_id"))
    def read_run_metrics(self, run_id: str) -> RunMetrics | None:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM run_metrics WHERE run_id = ?",
                (run_id,),
            ).fetchone()

        if row is None:
            return None

        _validate_required_cols(row=row, required_cols=RUN_METRICS_REQUIRED_COLS)
        metrics = _parse_metrics_json(raw=row["metrics"])
        return RunMetrics(
            run_id=row["run_id"],
            metrics=metrics,
            created_at=row["created_at"],
        )
