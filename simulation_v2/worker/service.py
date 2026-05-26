"""Worker service: owns run/turn status transitions for queued work."""

from __future__ import annotations

from pathlib import Path

from simulation_v2.config import LocalSimulationConfig
from simulation_v2.db.connection import transaction
from simulation_v2.db.database import SimulationDatabase
from simulation_v2.db.errors import RunNotFoundError
from simulation_v2.seed.loader import import_seed_if_needed
from simulation_v2.worker.errors import RunNotRetryableError
from simulation_v2.worker.models import RunJob
from simulation_v2.worker.run_executor import execute_run


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
            import_seed_if_needed(job.run_id, config, repos, conn)
            execute_run(job.run_id, config, conn, repos)
            repos.update_run_status(job.run_id, "completed", conn)
    except (RunNotRetryableError, RunNotFoundError):
        raise
    except Exception as exc:
        with transaction(db_path) as conn:
            run = repos.get_run(job.run_id, conn)
            if run is not None and run.status == "running":
                repos.update_run_status(job.run_id, "failed", conn, error=str(exc))
        raise
