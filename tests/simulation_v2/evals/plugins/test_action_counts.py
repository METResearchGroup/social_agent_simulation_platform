"""Tests for action_counts eval plugin."""

from __future__ import annotations

from pathlib import Path

import pytest

from simulation_v2.config import LocalSimulationConfig
from simulation_v2.db.connection import transaction
from simulation_v2.db.database import SimulationDatabase
from simulation_v2.evals.interfaces import EvalContext
from simulation_v2.evals.plugins.action_counts import ActionCountsPlugin
from tests.simulation_v2.db import factories
from tests.simulation_v2.evals.conftest import EvalFixture, seed_eval_fixture_db


@pytest.fixture
def eval_fixture(tmp_path: Path) -> EvalFixture:
    return seed_eval_fixture_db(tmp_path / "eval_fixture.sqlite3")


def _metric_value(result, metric_name: str, action_type: str) -> float | None:
    for metric in result.metrics:
        if (
            metric.metric_name == metric_name
            and metric.metadata_json
            and metric.metadata_json.get("action_type") == action_type
        ):
            return metric.metric_value
    return None


class TestActionCountsPlugin:
    def test_turn_scope_passes_when_accepted_matches_executed(
        self, eval_fixture: EvalFixture
    ) -> None:
        with transaction(eval_fixture.db_path) as conn:
            context = EvalContext(
                repos=SimulationDatabase(eval_fixture.db_path).repos,
                conn=conn,
                run_id=eval_fixture.run_id,
                config=LocalSimulationConfig.default(),
                scope="turn",
                turn_id=eval_fixture.turn_id,
                turn_number=eval_fixture.turn_number,
            )
            result = ActionCountsPlugin().run(context)

        assert result.status == "passed"
        assert _metric_value(result, "proposed", "like_post") == 3.0
        assert _metric_value(result, "accepted", "like_post") == 2.0
        assert _metric_value(result, "rejected", "like_post") == 1.0
        assert _metric_value(result, "executed", "like_post") == 2.0
        assert _metric_value(result, "accepted", "follow_user") == 1.0
        assert _metric_value(result, "executed", "follow_user") == 1.0

    def test_fails_when_accepted_does_not_match_executed(self, tmp_path: Path) -> None:
        db_path = tmp_path / "mismatch.sqlite3"
        db = SimulationDatabase(db_path)
        db.initialize()
        run = factories.RunRecordFactory.create()
        turn = factories.TurnRecordFactory.create(run_id=run.run_id, turn_number=1)
        generation = factories.GenerationRecordFactory.create(
            run_id=run.run_id,
            turn_id=turn.turn_id,
            action_type="like_post",
        )
        with transaction(db_path) as conn:
            db.repos.insert_run(run, conn)
            db.repos.insert_turn(turn, conn)
            db.repos.insert_generation(generation, conn)
            db.repos.insert_proposed_action(
                factories.ProposedActionRecordFactory.create(
                    run_id=run.run_id,
                    turn_id=turn.turn_id,
                    action_type="like_post",
                    record_kind="validated",
                    generation_id=generation.generation_id,
                ),
                conn,
            )

        with transaction(db_path) as conn:
            context = EvalContext(
                repos=db.repos,
                conn=conn,
                run_id=run.run_id,
                config=LocalSimulationConfig.default(),
                scope="turn",
                turn_id=turn.turn_id,
                turn_number=turn.turn_number,
            )
            result = ActionCountsPlugin().run(context)

        assert result.status == "failed"
        assert any("like_post" in warning for warning in result.warnings)
