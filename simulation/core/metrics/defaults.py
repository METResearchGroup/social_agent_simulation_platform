from __future__ import annotations

from collections.abc import Callable

from simulation.core.metrics.builtins.actions import (
    RunActionTotalMetric,
    RunActionTotalsByTypeMetric,
    TurnActionCountsByTypeMetric,
    TurnActionTotalMetric,
)
from simulation.core.metrics.interfaces import Metric, MetricScope
from simulation.core.metrics.registry import MetricsRegistry

BUILTIN_METRICS: tuple[type[Metric], ...] = (
    TurnActionCountsByTypeMetric,
    TurnActionTotalMetric,
    RunActionTotalsByTypeMetric,
    RunActionTotalMetric,
)


def _validate_no_duplicate_metric_keys(
    *, metric_classes: tuple[type[Metric], ...]
) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for metric_cls in metric_classes:
        key = metric_cls.KEY
        if key in seen:
            duplicates.add(key)
        seen.add(key)
    if duplicates:
        dup_list = sorted(duplicates)
        raise ValueError(f"Duplicate metric keys in BUILTIN_METRICS: {dup_list}")


_validate_no_duplicate_metric_keys(metric_classes=BUILTIN_METRICS)

DEFAULT_TURN_METRIC_KEYS: list[str] = [
    metric_cls.KEY
    for metric_cls in BUILTIN_METRICS
    if metric_cls.SCOPE == MetricScope.TURN and metric_cls.DEFAULT_ENABLED
]

DEFAULT_RUN_METRIC_KEYS: list[str] = [
    metric_cls.KEY
    for metric_cls in BUILTIN_METRICS
    if metric_cls.SCOPE == MetricScope.RUN and metric_cls.DEFAULT_ENABLED
]


def get_registered_metrics_metadata() -> list[tuple[str, str, MetricScope, str]]:
    """Return (key, description, scope, author) for all builtin metrics, sorted by key."""
    result: list[tuple[str, str, MetricScope, str]] = [
        (metric_cls.KEY, metric_cls.DESCRIPTION, metric_cls.SCOPE, metric_cls.AUTHOR)
        for metric_cls in BUILTIN_METRICS
    ]
    return sorted(result, key=lambda t: t[0])


def create_default_metrics_registry() -> MetricsRegistry:
    metric_builders: dict[str, Callable[[], Metric]] = {
        metric_cls.KEY: metric_cls for metric_cls in BUILTIN_METRICS
    }
    return MetricsRegistry(metric_builders=metric_builders)
