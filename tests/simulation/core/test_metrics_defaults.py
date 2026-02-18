"""Unit tests for simulation.core.metrics.defaults."""

import pytest
from pydantic import TypeAdapter

from simulation.core.metrics.builtins.actions import (
    RunActionTotalMetric,
    RunActionTotalsByTypeMetric,
    TurnActionCountsByTypeMetric,
    TurnActionTotalMetric,
)
from simulation.core.metrics.defaults import (
    DEFAULT_RUN_METRIC_KEYS,
    DEFAULT_TURN_METRIC_KEYS,
    _validate_no_duplicate_metric_keys,
)
from simulation.core.metrics.interfaces import (
    Metric,
    MetricContext,
    MetricDeps,
    MetricScope,
)
from simulation.core.models.metrics import ComputedMetricResult, ComputedMetrics

_INT_ADAPTER = TypeAdapter(int)


def test_default_metric_key_lists_are_derived_and_ordered():
    assert DEFAULT_TURN_METRIC_KEYS == [
        TurnActionCountsByTypeMetric.KEY,
        TurnActionTotalMetric.KEY,
    ]
    assert DEFAULT_RUN_METRIC_KEYS == [
        RunActionTotalsByTypeMetric.KEY,
        RunActionTotalMetric.KEY,
    ]


def test_defaults_duplicate_key_validation_raises():
    class _M1(Metric):
        KEY = "turn.dup"
        SCOPE = MetricScope.TURN
        DESCRIPTION = "Test metric."
        AUTHOR = "test"

        @property
        def output_adapter(self):
            return _INT_ADAPTER

        def compute(
            self, *, ctx: MetricContext, deps: MetricDeps, prior: ComputedMetrics
        ) -> ComputedMetricResult:
            return 0

    class _M2(Metric):
        KEY = "turn.dup"
        SCOPE = MetricScope.TURN
        DESCRIPTION = "Test metric."
        AUTHOR = "test"

        @property
        def output_adapter(self):
            return _INT_ADAPTER

        def compute(
            self, *, ctx: MetricContext, deps: MetricDeps, prior: ComputedMetrics
        ) -> ComputedMetricResult:
            return 0

    with pytest.raises(ValueError, match="Duplicate metric keys"):
        _validate_no_duplicate_metric_keys(metric_classes=(_M1, _M2))
