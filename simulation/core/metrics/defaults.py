from __future__ import annotations

from collections.abc import Callable

from simulation.core.metrics.builtins.actions import (
    RunActionTotalMetric,
    RunActionTotalsByTypeMetric,
    TurnActionCountsByTypeMetric,
    TurnActionTotalMetric,
)
from simulation.core.metrics.interfaces import Metric
from simulation.core.metrics.registry import MetricsRegistry

DEFAULT_TURN_METRIC_KEYS: list[str] = [
    "turn.actions.counts_by_type",
    "turn.actions.total",
]

DEFAULT_RUN_METRIC_KEYS: list[str] = [
    "run.actions.total_by_type",
    "run.actions.total",
]


def create_default_metrics_registry() -> MetricsRegistry:
    metric_builders: dict[str, Callable[[], Metric]] = {
        "turn.actions.counts_by_type": TurnActionCountsByTypeMetric,
        "turn.actions.total": TurnActionTotalMetric,
        "run.actions.total_by_type": RunActionTotalsByTypeMetric,
        "run.actions.total": RunActionTotalMetric,
    }
    return MetricsRegistry(metric_builders=metric_builders)
