"""Integration tests for control plane dispatch and worker retry."""

from __future__ import annotations

from pathlib import Path

from simulation_v2.config import LocalSimulationConfig
from simulation_v2.control_plane.service import start_run
from simulation_v2.db.connection import transaction
from simulation_v2.db.database import SimulationDatabase
from simulation_v2.worker.models import RunJob
from simulation_v2.worker.service import run_job
from tests.simulation_v2.db import factories

FIXED_TS = "2026-05-26T12:00:00.000000+00:00"
FIXED_TS_2 = "2026-05-26T13:00:00.000000+00:00"


def test_dispatch_completes_run_end_to_end(tmp_path: Path) -> None:
    db_path = tmp_path / "test.sqlite3"
    config = LocalSimulationConfig.default().model_copy(update={"total_turns": 3})

    run_id = start_run(config, dispatch=True, db_path=db_path)

    db = SimulationDatabase(db_path)
    with transaction(db_path) as conn:
        run = db.repos.get_run(run_id, conn)
        turns = db.repos.list_turns_for_run(run_id, conn)

    assert run is not None
    assert run.status == "completed"
    assert len(turns) == config.total_turns
    assert all(turn.status == "completed" for turn in turns)


def test_dispatch_retry_skips_completed_turns(tmp_path: Path) -> None:
    db_path = tmp_path / "test.sqlite3"
    config = LocalSimulationConfig.default().model_copy(update={"total_turns": 3})
    run = factories.RunRecordFactory.create(config_json=config.model_dump(mode="json"))
    turn1 = factories.TurnRecordFactory.create(
        run_id=run.run_id, turn_number=1, status="pending"
    )
    turn2 = factories.TurnRecordFactory.create(
        run_id=run.run_id, turn_number=2, status="pending"
    )
    db = SimulationDatabase(db_path)
    db.initialize()
    with transaction(db_path) as conn:
        db.repos.insert_run(run, conn)
        db.repos.update_run_status(run.run_id, "running", conn, timestamp=FIXED_TS)
        db.repos.insert_turn(turn1, conn)
        db.repos.update_turn_status(turn1.turn_id, "running", conn, timestamp=FIXED_TS)
        db.repos.update_turn_status(
            turn1.turn_id, "completed", conn, timestamp=FIXED_TS_2
        )
        db.repos.insert_turn(turn2, conn)

    run_job(RunJob(run_id=run.run_id), db_path=db_path)

    with transaction(db_path) as conn:
        loaded_run = db.repos.get_run(run.run_id, conn)
        turns = db.repos.list_turns_for_run(run.run_id, conn)
        turn1_after = db.repos.get_turn_by_run_and_number(run.run_id, 1, conn)

    assert loaded_run is not None
    assert loaded_run.status == "completed"
    assert len(turns) == config.total_turns
    assert turn1_after is not None
    assert turn1_after.turn_id == turn1.turn_id
    assert turn1_after.status == "completed"
    assert all(turn.status == "completed" for turn in turns)
