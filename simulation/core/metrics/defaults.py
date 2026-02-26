from __future__ import annotations

from collections import Counter
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

REGISTERED_METRIC_KEYS: frozenset[str] = frozenset(
    metric_cls.KEY for metric_cls in BUILTIN_METRICS
)

KEY_TO_SCOPE: dict[str, MetricScope] = {
    metric_cls.KEY: metric_cls.SCOPE for metric_cls in BUILTIN_METRICS
}

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


def get_default_metric_keys() -> list[str]:
    """Return sorted unique union of default turn and run metric keys."""
    return sorted(set(DEFAULT_TURN_METRIC_KEYS + DEFAULT_RUN_METRIC_KEYS))


def resolve_metric_keys_by_scope(
    metric_keys: list[str],
) -> tuple[list[str], list[str]]:
    """Split metric keys into turn-scoped and run-scoped lists.

    Args:
        metric_keys: List of metric keys to split.

    Returns:
        (turn_keys, run_keys) both sorted for determinism.

    Raises:
        ValueError: If metric_keys contains duplicate keys; if any key is not in
            REGISTERED_METRIC_KEYS; or if a key's scope is not TURN or RUN
            (e.g. unknown MetricScope from BUILTIN_METRICS).
    """
    counts = Counter(metric_keys)
    duplicate_keys = [k for k, c in counts.items() if c > 1]
    if duplicate_keys:
        raise ValueError(
            f"metric_keys contains duplicate keys: {sorted(duplicate_keys)}"
        )
    turn_keys: list[str] = []
    run_keys: list[str] = []
    for key in metric_keys:
        if key not in REGISTERED_METRIC_KEYS:
            raise ValueError(
                f"metric_keys contains unknown key '{key}'; "
                f"registered keys: {sorted(REGISTERED_METRIC_KEYS)}"
            )
        scope = KEY_TO_SCOPE[key]
        if scope == MetricScope.TURN:
            turn_keys.append(key)
        elif scope == MetricScope.RUN:
            run_keys.append(key)
        else:
            raise ValueError(
                f"metric key '{key}' has unknown MetricScope {scope!r}; "
                "only TURN and RUN are supported"
            )
    return (sorted(turn_keys), sorted(run_keys))


def get_registered_metrics_metadata() -> list[tuple[str, str, str, MetricScope, str]]:
    """Return (key, display_name, description, scope, author) for all builtin metrics, sorted by key."""
    result: list[tuple[str, str, str, MetricScope, str]] = [
        (
            metric_cls.KEY,
            metric_cls.DISPLAY_NAME,
            metric_cls.DESCRIPTION,
            metric_cls.SCOPE,
            metric_cls.AUTHOR,
        )
        for metric_cls in BUILTIN_METRICS
    ]
    return sorted(result, key=lambda t: t[0])


def create_default_metrics_registry() -> MetricsRegistry:
    metric_builders: dict[str, Callable[[], Metric]] = {
        metric_cls.KEY: metric_cls for metric_cls in BUILTIN_METRICS
    }
    return MetricsRegistry(metric_builders=metric_builders)
