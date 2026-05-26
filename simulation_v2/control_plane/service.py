"""Local control plane: creates queued runs and optionally dispatches work."""

from __future__ import annotations

from pathlib import Path

from simulation_v2.config import LocalSimulationConfig
from simulation_v2.control_plane.dispatcher import dispatch_now
from simulation_v2.db.connection import transaction
from simulation_v2.db.database import SimulationDatabase
from simulation_v2.db.models import RunRecord, TurnRecord
from simulation_v2.ids import new_run_id
from simulation_v2.time import get_current_timestamp


def start_run(
    config: LocalSimulationConfig,
    *,
    dispatch: bool = True,
    db_path: Path | None = None,
) -> str:
    resolved_db_path = db_path or config.storage.db_path
    db = SimulationDatabase(resolved_db_path)
    db.initialize()

    run_id = new_run_id()
    run = RunRecord(
        run_id=run_id,
        status="queued",
        config_json=config.model_dump(mode="json"),
        created_at=get_current_timestamp(),
    )
    with transaction(resolved_db_path) as conn:
        db.repos.insert_run(run, conn)

    if dispatch:
        dispatch_now(run_id, db_path=resolved_db_path)

    return run_id


def get_run_summary(
    run_id: str, *, db_path: Path
) -> tuple[RunRecord, list[TurnRecord]]:
    db = SimulationDatabase(db_path)
    with transaction(db_path) as conn:
        run = db.repos.get_run(run_id, conn)
        if run is None:
            raise ValueError(f"Run not found: {run_id}")
        turns = db.repos.list_turns_for_run(run_id, conn)
    return run, turns
