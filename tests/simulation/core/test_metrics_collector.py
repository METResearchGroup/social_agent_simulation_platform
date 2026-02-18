"""Unit tests for simulation.core.metrics.collector."""

from unittest.mock import Mock

import pytest

from simulation.core.exceptions import MetricsComputationError
from simulation.core.metrics.collector import MetricsCollector
from simulation.core.metrics.interfaces import (
    Metric,
    MetricContext,
    MetricDeps,
    MetricScope,
)
from simulation.core.metrics.registry import MetricsRegistry


class _ConstMetric(Metric):
    def __init__(
        self,
        *,
        key: str,
        scope: MetricScope,
        value: int,
        requires: tuple[str, ...] = (),
    ):
        self._key = key
        self._scope = scope
        self._value = value
        self._requires = requires

    @property
    def key(self) -> str:
        return self._key

    @property
    def scope(self) -> MetricScope:
        return self._scope

    @property
    def requires(self) -> tuple[str, ...]:
        return self._requires

    def compute(self, *, ctx: MetricContext, deps: MetricDeps, prior: dict) -> int:  # type: ignore[override]
        return self._value


class _DerivedSumMetric(Metric):
    def __init__(self, *, key: str, scope: MetricScope, requires: tuple[str, ...]):
        self._key = key
        self._scope = scope
        self._requires = requires

    @property
    def key(self) -> str:
        return self._key

    @property
    def scope(self) -> MetricScope:
        return self._scope

    @property
    def requires(self) -> tuple[str, ...]:
        return self._requires

    def compute(self, *, ctx: MetricContext, deps: MetricDeps, prior: dict) -> int:  # type: ignore[override]
        return sum(int(prior[k]) for k in self._requires)


class _BoomMetric(Metric):
    @property
    def key(self) -> str:
        return "turn.boom"

    @property
    def scope(self) -> MetricScope:
        return MetricScope.TURN

    def compute(self, *, ctx: MetricContext, deps: MetricDeps, prior: dict) -> int:  # type: ignore[override]
        raise ValueError("boom")


class TestMetricsCollectorResolveOrder:
    """Tests for deterministic dependency ordering."""

    def test_orders_dependencies_before_dependents(self):
        """Dependencies are evaluated before dependents in stable order."""
        registry = MetricsRegistry(
            metric_builders={
                "turn.a": lambda: _ConstMetric(
                    key="turn.a", scope=MetricScope.TURN, value=1
                ),
                "turn.b": lambda: _ConstMetric(
                    key="turn.b", scope=MetricScope.TURN, value=2
                ),
                "turn.sum": lambda: _DerivedSumMetric(
                    key="turn.sum",
                    scope=MetricScope.TURN,
                    requires=("turn.a", "turn.b"),
                ),
            }
        )

        deps = MetricDeps(run_repo=Mock(), metrics_repo=Mock(), sql_executor=None)
        collector = MetricsCollector(
            registry=registry,
            turn_metric_keys=["turn.sum"],
            run_metric_keys=[],
            deps=deps,
        )

        result = collector.collect_turn_metrics(run_id="run_x", turn_number=0)

        expected_result = {"turn.a": 1, "turn.b": 2, "turn.sum": 3}
        assert result == expected_result


class TestMetricsCollectorFailures:
    """Tests for fail-fast behavior."""

    def test_raises_metrics_computation_error(self):
        """Metric exceptions are wrapped into MetricsComputationError with key context."""
        registry = MetricsRegistry(metric_builders={"turn.boom": _BoomMetric})
        deps = MetricDeps(run_repo=Mock(), metrics_repo=Mock(), sql_executor=None)
        collector = MetricsCollector(
            registry=registry,
            turn_metric_keys=["turn.boom"],
            run_metric_keys=[],
            deps=deps,
        )

        with pytest.raises(MetricsComputationError) as exc_info:
            collector.collect_turn_metrics(run_id="run_x", turn_number=0)

        assert exc_info.value.metric_key == "turn.boom"
        assert exc_info.value.run_id == "run_x"
        assert exc_info.value.turn_number == 0
