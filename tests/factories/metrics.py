from __future__ import annotations

from simulation.core.models.metrics import ComputedMetrics, RunMetrics, TurnMetrics
from tests.factories.base import BaseFactory


class TurnMetricsFactory(BaseFactory[TurnMetrics]):
    @classmethod
    def create(
        cls,
        *,
        run_id: str = "run_123",
        turn_number: int = 0,
        metrics: ComputedMetrics | None = None,
        created_at: str = "2024_01_01-12:00:00",
    ) -> TurnMetrics:
        return TurnMetrics(
            run_id=run_id,
            turn_number=turn_number,
            metrics=metrics if metrics is not None else {"turn.actions.total": 0},
            created_at=created_at,
        )


class RunMetricsFactory(BaseFactory[RunMetrics]):
    @classmethod
    def create(
        cls,
        *,
        run_id: str = "run_123",
        metrics: ComputedMetrics | None = None,
        created_at: str = "2024_01_01-12:00:00",
    ) -> RunMetrics:
        return RunMetrics(
            run_id=run_id,
            metrics=metrics if metrics is not None else {"run.actions.total": 0},
            created_at=created_at,
        )
