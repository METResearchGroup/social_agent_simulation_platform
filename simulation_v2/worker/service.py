"""Worker service: owns run/turn status transitions for queued work."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from simulation_v2.config import LocalSimulationConfig
from simulation_v2.db.connection import transaction
from simulation_v2.db.database import SimulationDatabase
from simulation_v2.db.errors import RunNotFoundError
from simulation_v2.db.models import TurnRecord
from simulation_v2.db.repositories import SimulationRepositories
from simulation_v2.ids import new_turn_id
from simulation_v2.time import get_current_timestamp
from simulation_v2.worker.errors import RunNotRetryableError
from simulation_v2.worker.models import RunJob


def _execute_turn_stub() -> None:
    """Placeholder for PR 5+ turn execution."""
    pass


def _run_turns_for_run(
    run_id: str,
    config: LocalSimulationConfig,
    conn: sqlite3.Connection,
    repos: SimulationRepositories,
) -> None:
    for turn_number in range(1, config.total_turns + 1):
        existing = repos.get_turn_by_run_and_number(run_id, turn_number, conn)
        if existing is not None and existing.status == "completed":
            continue

        if existing is None:
            turn = TurnRecord(
                turn_id=new_turn_id(),
                run_id=run_id,
                turn_number=turn_number,
                status="pending",
                created_at=get_current_timestamp(),
            )
            repos.insert_turn(turn, conn)
            turn_id = turn.turn_id
        else:
            turn_id = existing.turn_id

        repos.update_turn_status(turn_id, "running", conn)
        _execute_turn_stub()
        repos.update_turn_status(turn_id, "completed", conn)


def run_job(job: RunJob, *, db_path: Path) -> None:
    db = SimulationDatabase(db_path)
    repos = db.repos

    try:
        with transaction(db_path) as conn:
            run = repos.get_run(job.run_id, conn)
            if run is None:
                raise RunNotFoundError(job.run_id)
            if run.status == "completed":
                return
            if run.status == "failed":
                raise RunNotRetryableError(job.run_id, run.status)
            if run.status not in ("queued", "running"):
                raise ValueError(f"Unexpected run status: {run.status!r}")

            if run.status == "queued":
                repos.update_run_status(job.run_id, "running", conn)

            config = LocalSimulationConfig.model_validate(run.config_json)
            _run_turns_for_run(job.run_id, config, conn, repos)
            repos.update_run_status(job.run_id, "completed", conn)
    except (RunNotRetryableError, RunNotFoundError):
        raise
    except Exception as exc:
        with transaction(db_path) as conn:
            run = repos.get_run(job.run_id, conn)
            if run is not None and run.status == "running":
                repos.update_run_status(job.run_id, "failed", conn, error=str(exc))
        raise
