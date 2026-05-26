"""Unit tests for simulation_v2 worker service."""

from __future__ import annotations

from pathlib import Path

import pytest

from simulation_v2.config import LocalSimulationConfig
from simulation_v2.db.connection import transaction
from simulation_v2.db.database import SimulationDatabase
from simulation_v2.worker.errors import RunNotRetryableError
from simulation_v2.worker.models import RunJob
from simulation_v2.worker.service import run_job
from tests.simulation_v2.db import factories

FIXED_TS = "2026-05-26T12:00:00.000000+00:00"
FIXED_TS_2 = "2026-05-26T13:00:00.000000+00:00"


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "test.sqlite3"
    SimulationDatabase(path).initialize()
    return path


def _small_config(**overrides: object) -> LocalSimulationConfig:
    return LocalSimulationConfig.default().model_copy(
        update={"total_turns": 3, **overrides}
    )


class TestRunJob:
    def test_run_job_completes_all_turns_from_queued(self, db_path: Path) -> None:
        config = _small_config()
        run = factories.RunRecordFactory.create(
            config_json=config.model_dump(mode="json")
        )
        db = SimulationDatabase(db_path)
        with transaction(db_path) as conn:
            db.repos.insert_run(run, conn)

        run_job(RunJob(run_id=run.run_id), db_path=db_path)

        with transaction(db_path) as conn:
            loaded_run = db.repos.get_run(run.run_id, conn)
            turns = db.repos.list_turns_for_run(run.run_id, conn)

        assert loaded_run is not None
        assert loaded_run.status == "completed"
        assert len(turns) == config.total_turns
        assert all(turn.status == "completed" for turn in turns)

    def test_run_job_idempotent_when_run_already_completed(self, db_path: Path) -> None:
        config = _small_config()
        run = factories.RunRecordFactory.create(
            config_json=config.model_dump(mode="json")
        )
        db = SimulationDatabase(db_path)
        with transaction(db_path) as conn:
            db.repos.insert_run(run, conn)
            db.repos.update_run_status(run.run_id, "running", conn, timestamp=FIXED_TS)
            db.repos.update_run_status(
                run.run_id, "completed", conn, timestamp=FIXED_TS_2
            )

        run_job(RunJob(run_id=run.run_id), db_path=db_path)

        with transaction(db_path) as conn:
            loaded_run = db.repos.get_run(run.run_id, conn)
            turns = db.repos.list_turns_for_run(run.run_id, conn)

        assert loaded_run is not None
        assert loaded_run.status == "completed"
        assert turns == []

    def test_run_job_resumes_running_run_skips_completed_turns(
        self, db_path: Path
    ) -> None:
        config = _small_config(total_turns=3)
        run = factories.RunRecordFactory.create(
            config_json=config.model_dump(mode="json")
        )
        turn1 = factories.TurnRecordFactory.create(
            run_id=run.run_id, turn_number=1, status="pending"
        )
        db = SimulationDatabase(db_path)
        with transaction(db_path) as conn:
            db.repos.insert_run(run, conn)
            db.repos.update_run_status(run.run_id, "running", conn, timestamp=FIXED_TS)
            db.repos.insert_turn(turn1, conn)
            db.repos.update_turn_status(
                turn1.turn_id, "running", conn, timestamp=FIXED_TS
            )
            db.repos.update_turn_status(
                turn1.turn_id, "completed", conn, timestamp=FIXED_TS_2
            )

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

    def test_run_job_rejects_failed_run(self, db_path: Path) -> None:
        config = _small_config()
        run = factories.RunRecordFactory.create(
            config_json=config.model_dump(mode="json")
        )
        db = SimulationDatabase(db_path)
        with transaction(db_path) as conn:
            db.repos.insert_run(run, conn)
            db.repos.update_run_status(run.run_id, "running", conn, timestamp=FIXED_TS)
            db.repos.update_run_status(
                run.run_id,
                "failed",
                conn,
                error="previous failure",
                timestamp=FIXED_TS_2,
            )

        with pytest.raises(RunNotRetryableError):
            run_job(RunJob(run_id=run.run_id), db_path=db_path)

        with transaction(db_path) as conn:
            loaded_run = db.repos.get_run(run.run_id, conn)

        assert loaded_run is not None
        assert loaded_run.status == "failed"
