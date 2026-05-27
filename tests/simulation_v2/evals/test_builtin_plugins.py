"""Integration tests for built-in eval plugins via the runner."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

import simulation_v2.evals  # noqa: F401 — registers builtins
from simulation_v2.config import EvalConfig, LocalSimulationConfig
from simulation_v2.db.connection import transaction
from simulation_v2.db.database import SimulationDatabase
from simulation_v2.evals.runner import run_run_evals, run_turn_evals
from tests.simulation_v2.evals.conftest import EvalFixture, seed_eval_fixture_db

BUILTIN_PLUGINS = [
    "action_counts",
    "invalid_action_rate",
    "feed_coverage",
    "llm_structured_output",
]


def _eval_config() -> EvalConfig:
    return EvalConfig(
        enabled=True,
        fail_run_on_error=False,
        turn_plugins=BUILTIN_PLUGINS,
        run_plugins=BUILTIN_PLUGINS,
    )


@pytest.fixture
def eval_fixture(tmp_path: Path) -> EvalFixture:
    return seed_eval_fixture_db(tmp_path / "builtin_eval.sqlite3")


def _count_eval_runs(db_path: Path) -> int:
    with transaction(db_path) as conn:
        row = conn.execute("SELECT COUNT(*) AS count FROM eval_runs").fetchone()
    return int(row["count"])


class TestBuiltinPluginsIntegration:
    def test_run_turn_evals_executes_all_builtin_plugins(
        self, eval_fixture: EvalFixture, caplog: pytest.LogCaptureFixture
    ) -> None:
        db = SimulationDatabase(eval_fixture.db_path)
        config = LocalSimulationConfig.default().model_copy(
            update={"evals": _eval_config()}
        )

        with caplog.at_level(logging.INFO, logger="simulation_v2.evals.runner"):
            with transaction(eval_fixture.db_path) as conn:
                summaries = run_turn_evals(
                    eval_fixture.run_id,
                    eval_fixture.turn_id,
                    eval_fixture.turn_number,
                    config,
                    db.repos,
                    conn,
                )

        assert len(summaries) == 4
        assert {summary.plugin_name for summary in summaries} == set(BUILTIN_PLUGINS)
        assert _count_eval_runs(eval_fixture.db_path) == 4
        assert any("eval turn summary" in record.message for record in caplog.records)

    def test_run_run_evals_executes_all_builtin_plugins(
        self, eval_fixture: EvalFixture
    ) -> None:
        db = SimulationDatabase(eval_fixture.db_path)
        config = LocalSimulationConfig.default().model_copy(
            update={"evals": _eval_config()}
        )

        with transaction(eval_fixture.db_path) as conn:
            summaries = run_run_evals(eval_fixture.run_id, config, db.repos, conn)

        assert len(summaries) == 4
        assert _count_eval_runs(eval_fixture.db_path) == 4

    def test_default_config_plugin_names_resolve(self) -> None:
        from simulation_v2.evals.registry import get_eval_plugin

        for name in BUILTIN_PLUGINS:
            assert get_eval_plugin(name) is not None
