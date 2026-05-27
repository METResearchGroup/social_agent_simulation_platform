"""Tests for invalid_action_rate eval plugin."""

from __future__ import annotations

from pathlib import Path

import pytest

from simulation_v2.config import LocalSimulationConfig
from simulation_v2.db.connection import transaction
from simulation_v2.db.database import SimulationDatabase
from simulation_v2.evals.interfaces import EvalContext
from simulation_v2.evals.plugins.invalid_action_rate import InvalidActionRatePlugin
from tests.simulation_v2.evals.conftest import EvalFixture, seed_eval_fixture_db


@pytest.fixture
def eval_fixture(tmp_path: Path) -> EvalFixture:
    return seed_eval_fixture_db(tmp_path / "eval_fixture.sqlite3")


class TestInvalidActionRatePlugin:
    def test_reports_rejection_rate_for_filter(self, eval_fixture: EvalFixture) -> None:
        db = SimulationDatabase(eval_fixture.db_path)
        with transaction(eval_fixture.db_path) as conn:
            context = EvalContext(
                repos=db.repos,
                conn=conn,
                run_id=eval_fixture.run_id,
                config=LocalSimulationConfig.default(),
                scope="turn",
                turn_id=eval_fixture.turn_id,
                turn_number=eval_fixture.turn_number,
            )
            result = InvalidActionRatePlugin().run(context)

        assert result.status == "passed"
        rate_metrics = [
            m
            for m in result.metrics
            if m.metric_name == "rate"
            and m.metadata_json
            and m.metadata_json.get("filter_id") == "duplicate_like"
        ]
        assert len(rate_metrics) == 1
        assert rate_metrics[0].metric_value == pytest.approx(1 / 3)
        rejected = next(
            m
            for m in result.metrics
            if m.metric_name == "rejected_count"
            and m.metadata_json
            and m.metadata_json.get("filter_id") == "duplicate_like"
        )
        assert rejected.metric_value == 1.0
