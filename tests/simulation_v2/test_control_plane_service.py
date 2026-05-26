"""Unit tests for simulation_v2 control plane service."""

from __future__ import annotations

from pathlib import Path

from simulation_v2.config import LocalSimulationConfig
from simulation_v2.control_plane.service import start_run
from simulation_v2.db.connection import transaction
from simulation_v2.db.database import SimulationDatabase


def test_start_run_inserts_queued_run_with_config_json(tmp_path: Path) -> None:
    db_path = tmp_path / "test.sqlite3"
    config = LocalSimulationConfig.default().model_copy(update={"total_turns": 2})

    run_id = start_run(config, dispatch=False, db_path=db_path)

    db = SimulationDatabase(db_path)
    with transaction(db_path) as conn:
        loaded = db.repos.get_run(run_id, conn)

    assert loaded is not None
    assert loaded.status == "queued"
    assert LocalSimulationConfig.model_validate(loaded.config_json) == config


def test_start_run_initializes_schema_idempotently(tmp_path: Path) -> None:
    db_path = tmp_path / "test.sqlite3"
    config = LocalSimulationConfig.default()

    run_id_1 = start_run(config, dispatch=False, db_path=db_path)
    run_id_2 = start_run(config, dispatch=False, db_path=db_path)

    assert run_id_1 != run_id_2

    db = SimulationDatabase(db_path)
    with transaction(db_path) as conn:
        run_1 = db.repos.get_run(run_id_1, conn)
        run_2 = db.repos.get_run(run_id_2, conn)

    assert run_1 is not None
    assert run_2 is not None
    assert run_1.status == "queued"
    assert run_2.status == "queued"


def test_start_run_uses_custom_db_path_override(tmp_path: Path) -> None:
    custom_path = tmp_path / "custom.sqlite3"
    config = LocalSimulationConfig.default()

    run_id = start_run(config, dispatch=False, db_path=custom_path)

    assert custom_path.exists()

    db = SimulationDatabase(custom_path)
    with transaction(custom_path) as conn:
        loaded = db.repos.get_run(run_id, conn)

    assert loaded is not None
    assert loaded.status == "queued"
