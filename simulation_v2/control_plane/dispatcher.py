"""In-process dispatch from control plane to worker."""

from __future__ import annotations

from pathlib import Path

from simulation_v2.worker.models import RunJob
from simulation_v2.worker.service import run_job


def dispatch_now(run_id: str, *, db_path: Path) -> None:
    run_job(RunJob(run_id=run_id), db_path=db_path)
