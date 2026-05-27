"""Tests for feed_coverage eval plugin."""

from __future__ import annotations

from pathlib import Path

import pytest

from simulation_v2.config import LocalSimulationConfig
from simulation_v2.db.connection import transaction
from simulation_v2.db.database import SimulationDatabase
from simulation_v2.evals.interfaces import EvalContext
from simulation_v2.evals.plugins.feed_coverage import FeedCoveragePlugin
from tests.simulation_v2.evals.conftest import EvalFixture, seed_eval_fixture_db


@pytest.fixture
def eval_fixture(tmp_path: Path) -> EvalFixture:
    return seed_eval_fixture_db(tmp_path / "eval_fixture.sqlite3")


def _metric(result, name: str) -> float:
    return next(m.metric_value for m in result.metrics if m.metric_name == name)


class TestFeedCoveragePlugin:
    def test_turn_scope_detects_feed_violations(
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
            result = FeedCoveragePlugin().run(context)

        assert result.status == "failed"
        assert _metric(result, "users_total") == 6.0
        assert _metric(result, "users_missing_feed") == 1.0
        assert _metric(result, "empty_feeds") == 1.0
        assert _metric(result, "duplicate_post_feeds") == 1.0
        assert _metric(result, "self_authored_feeds") == 1.0
        assert result.warnings
