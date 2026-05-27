"""Unit tests for simulation_v2 eval runner."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import pytest

from simulation_v2.config import EvalConfig, LocalSimulationConfig
from simulation_v2.db.connection import transaction
from simulation_v2.db.database import SimulationDatabase
from simulation_v2.db.models.evals import EvalScope
from simulation_v2.evals.interfaces import EvalContext, EvalMetricDraft, EvalResult
from simulation_v2.evals.registry import _PLUGINS, register_eval_plugin
from simulation_v2.evals.runner import (
    EvalExecutionError,
    run_run_evals,
    run_turn_evals,
)
from tests.simulation_v2.db import factories


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "test.sqlite3"
    SimulationDatabase(path).initialize()
    return path


@pytest.fixture
def clean_eval_registry():
    original = _PLUGINS.copy()
    yield
    _PLUGINS.clear()
    _PLUGINS.update(original)


class _PassingTurnPlugin:
    name: ClassVar[str] = "test_pass"
    scopes: ClassVar[frozenset[EvalScope]] = frozenset({"turn"})

    def run(self, context: EvalContext) -> EvalResult:
        return EvalResult(
            plugin_name=self.name,
            status="passed",
            metrics=[
                EvalMetricDraft(
                    metric_name="example_metric",
                    metric_value=1.0,
                    metadata_json={"source": "test"},
                )
            ],
        )


class _FailingTurnPlugin:
    name: ClassVar[str] = "test_fail"
    scopes: ClassVar[frozenset[EvalScope]] = frozenset({"turn"})

    def run(self, context: EvalContext) -> EvalResult:
        return EvalResult(
            plugin_name=self.name,
            status="failed",
            metrics=[],
            warnings=["deliberate failure"],
        )


class _RaisingTurnPlugin:
    name: ClassVar[str] = "test_raise"
    scopes: ClassVar[frozenset[EvalScope]] = frozenset({"turn"})

    def run(self, context: EvalContext) -> EvalResult:
        raise RuntimeError("plugin exploded")


class _PassingRunPlugin:
    name: ClassVar[str] = "test_run_pass"
    scopes: ClassVar[frozenset[EvalScope]] = frozenset({"run"})

    def run(self, context: EvalContext) -> EvalResult:
        return EvalResult(
            plugin_name=self.name,
            status="passed",
            metrics=[EvalMetricDraft(metric_name="run_metric", metric_value=2.0)],
        )


def _eval_config(**overrides: object) -> EvalConfig:
    defaults: dict[str, object] = {
        "enabled": True,
        "fail_run_on_error": False,
        "turn_plugins": [],
        "run_plugins": [],
    }
    defaults.update(overrides)
    return EvalConfig.model_validate(defaults)


def _insert_run_and_turn(db_path: Path) -> tuple[SimulationDatabase, str, str, int]:
    db = SimulationDatabase(db_path)
    run = factories.RunRecordFactory.create()
    turn = factories.TurnRecordFactory.create(run_id=run.run_id, turn_number=1)
    with transaction(db_path) as conn:
        db.repos.insert_run(run, conn)
        db.repos.insert_turn(turn, conn)
    return db, run.run_id, turn.turn_id, turn.turn_number


def _count_eval_runs(db_path: Path) -> int:
    with transaction(db_path) as conn:
        row = conn.execute("SELECT COUNT(*) AS count FROM eval_runs").fetchone()
    return int(row["count"])


def _count_eval_metrics(db_path: Path) -> int:
    with transaction(db_path) as conn:
        row = conn.execute("SELECT COUNT(*) AS count FROM eval_metrics").fetchone()
    return int(row["count"])


def _list_eval_runs(db_path: Path) -> list[dict[str, object]]:
    with transaction(db_path) as conn:
        rows = conn.execute("SELECT * FROM eval_runs ORDER BY created_at").fetchall()
    return [dict(row) for row in rows]


class TestRunTurnEvals:
    def test_passing_turn_plugin_persists_completed_eval_run(
        self, db_path: Path, clean_eval_registry
    ) -> None:
        register_eval_plugin(_PassingTurnPlugin())
        db, run_id, turn_id, turn_number = _insert_run_and_turn(db_path)
        config = LocalSimulationConfig.default().model_copy(
            update={"evals": _eval_config(turn_plugins=["test_pass"])}
        )

        with transaction(db_path) as conn:
            summaries = run_turn_evals(
                run_id, turn_id, turn_number, config, db.repos, conn
            )

        assert len(summaries) == 1
        assert summaries[0].plugin_name == "test_pass"
        assert summaries[0].status == "completed"
        assert len(summaries[0].metrics) == 1
        assert _count_eval_runs(db_path) == 1
        assert _count_eval_metrics(db_path) == 1

        eval_runs = _list_eval_runs(db_path)
        assert eval_runs[0]["status"] == "completed"
        assert eval_runs[0]["error"] is None
        assert eval_runs[0]["turn_id"] == turn_id

    def test_failing_turn_plugin_persists_failed_eval_run_without_raising(
        self, db_path: Path, clean_eval_registry
    ) -> None:
        register_eval_plugin(_FailingTurnPlugin())
        db, run_id, turn_id, turn_number = _insert_run_and_turn(db_path)
        config = LocalSimulationConfig.default().model_copy(
            update={"evals": _eval_config(turn_plugins=["test_fail"])}
        )

        with transaction(db_path) as conn:
            summaries = run_turn_evals(
                run_id, turn_id, turn_number, config, db.repos, conn
            )

        assert len(summaries) == 1
        assert summaries[0].status == "failed"
        eval_runs = _list_eval_runs(db_path)
        assert eval_runs[0]["status"] == "failed"
        assert eval_runs[0]["error"] == "deliberate failure"

    def test_fail_run_on_error_raises(self, db_path: Path, clean_eval_registry) -> None:
        register_eval_plugin(_FailingTurnPlugin())
        db, run_id, turn_id, turn_number = _insert_run_and_turn(db_path)
        config = LocalSimulationConfig.default().model_copy(
            update={
                "evals": _eval_config(
                    turn_plugins=["test_fail"],
                    fail_run_on_error=True,
                )
            }
        )

        with transaction(db_path) as conn:
            with pytest.raises(EvalExecutionError):
                run_turn_evals(run_id, turn_id, turn_number, config, db.repos, conn)

        assert _count_eval_runs(db_path) == 1

    def test_evals_disabled_writes_no_rows(
        self, db_path: Path, clean_eval_registry
    ) -> None:
        register_eval_plugin(_PassingTurnPlugin())
        db, run_id, turn_id, turn_number = _insert_run_and_turn(db_path)
        config = LocalSimulationConfig.default().model_copy(
            update={"evals": _eval_config(enabled=False, turn_plugins=["test_pass"])}
        )

        with transaction(db_path) as conn:
            summaries = run_turn_evals(
                run_id, turn_id, turn_number, config, db.repos, conn
            )

        assert summaries == []
        assert _count_eval_runs(db_path) == 0
        assert _count_eval_metrics(db_path) == 0

    def test_raising_plugin_persists_failed_eval_run(
        self, db_path: Path, clean_eval_registry
    ) -> None:
        register_eval_plugin(_RaisingTurnPlugin())
        db, run_id, turn_id, turn_number = _insert_run_and_turn(db_path)
        config = LocalSimulationConfig.default().model_copy(
            update={"evals": _eval_config(turn_plugins=["test_raise"])}
        )

        with transaction(db_path) as conn:
            summaries = run_turn_evals(
                run_id, turn_id, turn_number, config, db.repos, conn
            )

        assert summaries[0].status == "failed"
        eval_runs = _list_eval_runs(db_path)
        assert eval_runs[0]["error"] == "plugin exploded"


class TestRunRunEvals:
    def test_run_scope_sets_turn_id_none(
        self, db_path: Path, clean_eval_registry
    ) -> None:
        register_eval_plugin(_PassingRunPlugin())
        db = SimulationDatabase(db_path)
        run = factories.RunRecordFactory.create()
        with transaction(db_path) as conn:
            db.repos.insert_run(run, conn)

        config = LocalSimulationConfig.default().model_copy(
            update={"evals": _eval_config(run_plugins=["test_run_pass"])}
        )

        with transaction(db_path) as conn:
            summaries = run_run_evals(run.run_id, config, db.repos, conn)

        assert len(summaries) == 1
        assert summaries[0].status == "completed"
        eval_runs = _list_eval_runs(db_path)
        assert eval_runs[0]["scope"] == "run"
        assert eval_runs[0]["turn_id"] is None
