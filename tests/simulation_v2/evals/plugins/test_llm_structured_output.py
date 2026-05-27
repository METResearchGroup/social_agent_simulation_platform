"""Tests for llm_structured_output eval plugin."""

from __future__ import annotations

from pathlib import Path

import pytest

from simulation_v2.config import LocalSimulationConfig
from simulation_v2.db.connection import transaction
from simulation_v2.db.database import SimulationDatabase
from simulation_v2.evals.interfaces import EvalContext
from simulation_v2.evals.plugins.llm_structured_output import LlmStructuredOutputPlugin
from tests.simulation_v2.evals.conftest import EvalFixture, seed_eval_fixture_db


@pytest.fixture
def eval_fixture(tmp_path: Path) -> EvalFixture:
    return seed_eval_fixture_db(tmp_path / "eval_fixture.sqlite3")


class TestLlmStructuredOutputPlugin:
    def test_reports_generation_counts_by_status(
        self, eval_fixture: EvalFixture
    ) -> None:
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
            result = LlmStructuredOutputPlugin().run(context)

        assert result.status == "passed"
        completed_like = next(
            m
            for m in result.metrics
            if m.metric_name == "generation_count"
            and m.metadata_json
            and m.metadata_json.get("action_type") == "like_post"
            and m.metadata_json.get("status") == "completed"
        )
        assert completed_like.metric_value == 2.0

        schema_failed = next(
            m
            for m in result.metrics
            if m.metric_name == "generation_count"
            and m.metadata_json
            and m.metadata_json.get("status") == "schema_failed"
        )
        assert schema_failed.metric_value == 1.0

        success_rate = next(
            m
            for m in result.metrics
            if m.metric_name == "success_rate"
            and m.metadata_json
            and m.metadata_json.get("action_type") == "like_post"
        )
        assert success_rate.metric_value == pytest.approx(0.5)
