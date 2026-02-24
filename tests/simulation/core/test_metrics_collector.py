"""Unit tests for simulation.core.metrics.collector."""

import json
from unittest.mock import Mock

import pytest
from pydantic import TypeAdapter

from simulation.core.exceptions import MetricsComputationError
from simulation.core.metrics.collector import MetricsCollector
from simulation.core.metrics.defaults import create_default_metrics_registry
from simulation.core.metrics.interfaces import (
    Metric,
    MetricContext,
    MetricDeps,
    MetricScope,
)
from simulation.core.metrics.registry import MetricsRegistry
from simulation.core.models.actions import TurnAction
from simulation.core.models.metrics import (
    ComputedMetricResult,
    ComputedMetrics,
    TurnMetrics,
)
from simulation.core.models.turns import TurnMetadata

_INT_ADAPTER = TypeAdapter(int)
_COUNTS_ADAPTER = TypeAdapter(dict[str, int])


def _const_metric_class(
    *,
    key: str,
    scope: MetricScope,
    value: int,
) -> type[Metric]:
    class _ConstMetricImpl(Metric):
        KEY = key
        SCOPE = scope
        VALUE = value
        DESCRIPTION = "Test metric."
        AUTHOR = "test"

        @property
        def output_adapter(self):
            return _INT_ADAPTER

        def compute(
            self, *, ctx: MetricContext, deps: MetricDeps, prior: ComputedMetrics
        ) -> ComputedMetricResult:
            return self.VALUE

    return _ConstMetricImpl


def _sum_metric_class(
    *,
    key: str,
    scope: MetricScope,
    requires_keys: tuple[str, ...],
) -> type[Metric]:
    class _SumMetricImpl(Metric):
        KEY = key
        SCOPE = scope
        REQUIRES = requires_keys
        DESCRIPTION = "Test metric."
        AUTHOR = "test"

        @property
        def output_adapter(self):
            return _INT_ADAPTER

        @property
        def requires(self) -> tuple[str, ...]:
            return self.REQUIRES

        def compute(
            self, *, ctx: MetricContext, deps: MetricDeps, prior: ComputedMetrics
        ) -> ComputedMetricResult:
            total = 0
            for k in self.REQUIRES:
                v = prior[k]
                assert isinstance(v, int)
                total += v
            return total

    return _SumMetricImpl


class _BoomMetric(Metric):
    KEY = "turn.boom"
    SCOPE = MetricScope.TURN
    DESCRIPTION = "Test metric."
    AUTHOR = "test"

    @property
    def output_adapter(self):
        return _INT_ADAPTER

    def compute(
        self, *, ctx: MetricContext, deps: MetricDeps, prior: ComputedMetrics
    ) -> ComputedMetricResult:
        raise ValueError("boom")


class TestMetricsCollectorOptionalKeysOverride:
    """Tests for optional turn_metric_keys/run_metric_keys override."""

    def test_collect_turn_metrics_uses_override_when_provided(self):
        """Passing turn_metric_keys overrides instance default."""
        registry = MetricsRegistry(
            metric_builders={
                "turn.a": _const_metric_class(
                    key="turn.a", scope=MetricScope.TURN, value=1
                ),
                "turn.b": _const_metric_class(
                    key="turn.b", scope=MetricScope.TURN, value=2
                ),
            }
        )
        deps = MetricDeps(run_repo=Mock(), metrics_repo=Mock(), sql_executor=None)
        collector = MetricsCollector(
            registry=registry,
            turn_metric_keys=["turn.a", "turn.b"],
            run_metric_keys=[],
            deps=deps,
        )

        result = collector.collect_turn_metrics(
            run_id="run_x",
            turn_number=0,
            turn_metric_keys=["turn.a"],
        )

        assert result == {"turn.a": 1}

    def test_collect_run_metrics_uses_override_when_provided(self):
        """Passing run_metric_keys overrides instance default."""
        registry = MetricsRegistry(
            metric_builders={
                "run.x": _const_metric_class(
                    key="run.x", scope=MetricScope.RUN, value=10
                ),
                "run.y": _const_metric_class(
                    key="run.y", scope=MetricScope.RUN, value=20
                ),
            }
        )
        deps = MetricDeps(run_repo=Mock(), metrics_repo=Mock(), sql_executor=None)
        collector = MetricsCollector(
            registry=registry,
            turn_metric_keys=[],
            run_metric_keys=["run.x", "run.y"],
            deps=deps,
        )

        result = collector.collect_run_metrics(
            run_id="run_x",
            run_metric_keys=["run.y"],
        )

        assert result == {"run.y": 20}


class TestMetricsCollectorResolveOrder:
    """Tests for deterministic dependency ordering."""

    def test_orders_dependencies_before_dependents(self):
        """Dependencies are evaluated before dependents in stable order."""
        registry = MetricsRegistry(
            metric_builders={
                "turn.a": _const_metric_class(
                    key="turn.a", scope=MetricScope.TURN, value=1
                ),
                "turn.b": _const_metric_class(
                    key="turn.b", scope=MetricScope.TURN, value=2
                ),
                "turn.sum": _sum_metric_class(
                    key="turn.sum",
                    scope=MetricScope.TURN,
                    requires_keys=("turn.a", "turn.b"),
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

        result = collector.collect_turn_metrics(
            run_id="run_x",
            turn_number=0,
            turn_metric_keys=["turn.a", "turn.b", "turn.sum"],
        )

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
            collector.collect_turn_metrics(
                run_id="run_x",
                turn_number=0,
                turn_metric_keys=["turn.boom"],
            )

        assert exc_info.value.metric_key == "turn.boom"
        assert exc_info.value.run_id == "run_x"
        assert exc_info.value.turn_number == 0

    def test_raises_on_invalid_json_value(self):
        """Non-JSON values are rejected by output schema validation."""

        class _BadJsonMetric(Metric):
            KEY = "turn.bad_json"
            SCOPE = MetricScope.TURN
            DESCRIPTION = "Test metric."
            AUTHOR = "test"

            @property
            def output_adapter(self):
                return _INT_ADAPTER

            def compute(
                self, *, ctx: MetricContext, deps: MetricDeps, prior: ComputedMetrics
            ) -> ComputedMetricResult:  # type: ignore[override]
                return {1}  # type: ignore[return-value]  # non-JSON value for test

        registry = MetricsRegistry(metric_builders={"turn.bad_json": _BadJsonMetric})
        deps = MetricDeps(run_repo=Mock(), metrics_repo=Mock(), sql_executor=None)
        collector = MetricsCollector(
            registry=registry,
            turn_metric_keys=["turn.bad_json"],
            run_metric_keys=[],
            deps=deps,
        )

        with pytest.raises(MetricsComputationError) as exc_info:
            collector.collect_turn_metrics(
                run_id="run_x",
                turn_number=0,
                turn_metric_keys=["turn.bad_json"],
            )

        assert exc_info.value.metric_key == "turn.bad_json"
        assert "schema validation" in str(exc_info.value).lower()

    def test_raises_on_wrong_output_shape(self):
        """Wrong JSON shape is rejected (e.g., dict[str,int] but got str values)."""

        class _WrongShapeMetric(Metric):
            KEY = "turn.wrong_shape"
            SCOPE = MetricScope.TURN
            DESCRIPTION = "Test metric."
            AUTHOR = "test"

            @property
            def output_adapter(self):
                return _COUNTS_ADAPTER

            def compute(
                self, *, ctx: MetricContext, deps: MetricDeps, prior: ComputedMetrics
            ) -> ComputedMetricResult:
                return {"x": "y"}

        registry = MetricsRegistry(
            metric_builders={"turn.wrong_shape": _WrongShapeMetric}
        )
        deps = MetricDeps(run_repo=Mock(), metrics_repo=Mock(), sql_executor=None)
        collector = MetricsCollector(
            registry=registry,
            turn_metric_keys=["turn.wrong_shape"],
            run_metric_keys=[],
            deps=deps,
        )

        with pytest.raises(MetricsComputationError) as exc_info:
            collector.collect_turn_metrics(
                run_id="run_x",
                turn_number=0,
                turn_metric_keys=["turn.wrong_shape"],
            )

        assert exc_info.value.metric_key == "turn.wrong_shape"
        assert "expected_schema" in str(exc_info.value)


def test_built_in_metrics_validate_and_serialize():
    """Built-in metrics emit JSON-serializable, schema-validated outputs."""
    run_repo = Mock()
    metrics_repo = Mock()

    run_id = "run_x"
    run_repo.get_run.return_value = object()
    run_repo.get_turn_metadata.return_value = TurnMetadata(
        run_id=run_id,
        turn_number=0,
        total_actions={
            TurnAction.LIKE: 1,
            TurnAction.COMMENT: 2,
            TurnAction.FOLLOW: 0,
        },
        created_at="2026-01-01T00:00:00",
    )
    run_repo.list_turn_metadata.return_value = [run_repo.get_turn_metadata.return_value]

    deps = MetricDeps(run_repo=run_repo, metrics_repo=metrics_repo, sql_executor=None)
    collector = MetricsCollector(
        registry=create_default_metrics_registry(),
        turn_metric_keys=["turn.actions.total"],
        run_metric_keys=["run.actions.total"],
        deps=deps,
    )

    turn_metrics_dict = collector.collect_turn_metrics(
        run_id=run_id,
        turn_number=0,
        turn_metric_keys=["turn.actions.total"],
    )
    json.dumps(turn_metrics_dict)  # should not raise
    TurnMetrics(
        run_id=run_id,
        turn_number=0,
        metrics=turn_metrics_dict,
        created_at="2026-01-01T00:00:00",
    )

    run_metrics_dict = collector.collect_run_metrics(
        run_id=run_id,
        run_metric_keys=["run.actions.total"],
    )
    json.dumps(run_metrics_dict)  # should not raise
