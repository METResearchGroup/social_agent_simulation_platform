from __future__ import annotations

from simulation.core.models.metrics import ComputedMetrics, RunMetrics, TurnMetrics
from tests.factories.base import BaseFactory
from tests.factories.context import get_faker


class TurnMetricsFactory(BaseFactory[TurnMetrics]):
    @classmethod
    def create(
        cls,
        *,
        run_id: str | None = None,
        turn_number: int = 0,
        metrics: ComputedMetrics | None = None,
        created_at: str = "2024_01_01-12:00:00",
    ) -> TurnMetrics:
        fake = get_faker()
        run_id_value = run_id if run_id is not None else f"run_{fake.uuid4()}"
        return TurnMetrics(
            run_id=run_id_value,
            turn_number=turn_number,
            metrics=metrics if metrics is not None else {"turn.actions.total": 0},
            created_at=created_at,
        )


class RunMetricsFactory(BaseFactory[RunMetrics]):
    @classmethod
    def create(
        cls,
        *,
        run_id: str | None = None,
        metrics: ComputedMetrics | None = None,
        created_at: str = "2024_01_01-12:00:00",
    ) -> RunMetrics:
        fake = get_faker()
        run_id_value = run_id if run_id is not None else f"run_{fake.uuid4()}"
        return RunMetrics(
            run_id=run_id_value,
            metrics=metrics if metrics is not None else {"run.actions.total": 0},
            created_at=created_at,
        )
