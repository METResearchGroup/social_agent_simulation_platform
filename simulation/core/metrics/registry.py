from __future__ import annotations

from collections.abc import Callable

from simulation.core.metrics.interfaces import Metric


class MetricsRegistry:
    """Central registry mapping metric keys to Metric factories."""

    def __init__(self, *, metric_builders: dict[str, Callable[[], Metric]]):
        self._metric_builders = dict(metric_builders)

    def get(self, *, metric_key: str) -> Metric:
        if metric_key not in self._metric_builders:
            raise KeyError(f"Unknown metric key: {metric_key}")
        return self._metric_builders[metric_key]()

    def has(self, *, metric_key: str) -> bool:
        return metric_key in self._metric_builders
