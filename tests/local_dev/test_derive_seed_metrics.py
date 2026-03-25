"""Tests for simulation.local_dev.derive_from_metadata."""

from simulation.core.models.actions import TurnAction
from simulation.local_dev.derive_from_metadata import (
    derive_turn_and_run_metrics_from_fixtures,
)
from tests.factories import RunFactory, TurnMetadataFactory


class TestDeriveSeedMetrics:
    def test_derive_turn_and_run_metrics_is_deterministic_and_sums_actions(
        self,
    ) -> None:
        run = RunFactory.create(run_id="run_derive_test", total_turns=2)
        tm0 = TurnMetadataFactory.create(
            run_id=run.run_id,
            turn_number=0,
            total_actions={TurnAction.LIKE: 2, TurnAction.FOLLOW: 1},
            created_at="2026-01-01T00:00:00Z",
        )
        tm1 = TurnMetadataFactory.create(
            run_id=run.run_id,
            turn_number=1,
            total_actions={TurnAction.POST: 3},
            created_at="2026-01-01T00:01:00Z",
        )
        tm_list = [tm0, tm1]

        turn_a, run_a = derive_turn_and_run_metrics_from_fixtures(
            runs=[run], turn_metadata=tm_list
        )
        turn_b, run_b = derive_turn_and_run_metrics_from_fixtures(
            runs=[run], turn_metadata=tm_list
        )
        assert turn_a == turn_b
        assert run_a == run_b
        assert len(turn_a) == 2
        assert len(run_a) == 1
        assert run_a[0].metrics["run.actions.total"] == 6
