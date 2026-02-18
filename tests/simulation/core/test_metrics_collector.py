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
from simulation.core.models.json_types import JsonObject, JsonValue
from simulation.core.models.metrics import TurnMetrics
from simulation.core.models.turns import TurnMetadata

_INT_ADAPTER = TypeAdapter(int)
_COUNTS_ADAPTER = TypeAdapter(dict[str, int])


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
    def output_adapter(self):
        return _INT_ADAPTER

    @property
    def requires(self) -> tuple[str, ...]:
        return self._requires

    def compute(
        self, *, ctx: MetricContext, deps: MetricDeps, prior: JsonObject
    ) -> JsonValue:
        return self._value  # int is a valid JsonValue


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
    def output_adapter(self):
        return _INT_ADAPTER

    @property
    def requires(self) -> tuple[str, ...]:
        return self._requires

    def compute(
        self, *, ctx: MetricContext, deps: MetricDeps, prior: JsonObject
    ) -> JsonValue:
        total = 0
        for k in self._requires:
            v = prior[k]
            assert isinstance(v, int)
            total += v
        return total


class _BoomMetric(Metric):
    @property
    def key(self) -> str:
        return "turn.boom"

    @property
    def scope(self) -> MetricScope:
        return MetricScope.TURN

    @property
    def output_adapter(self):
        return _INT_ADAPTER

    def compute(
        self, *, ctx: MetricContext, deps: MetricDeps, prior: JsonObject
    ) -> JsonValue:
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

    def test_raises_on_invalid_json_value(self):
        """Non-JSON values are rejected by output schema validation."""

        class _BadJsonMetric(Metric):
            @property
            def key(self) -> str:
                return "turn.bad_json"

            @property
            def scope(self) -> MetricScope:
                return MetricScope.TURN

            @property
            def output_adapter(self):
                return _INT_ADAPTER

            def compute(
                self, *, ctx: MetricContext, deps: MetricDeps, prior: JsonObject
            ) -> JsonValue:  # type: ignore[override]
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
            collector.collect_turn_metrics(run_id="run_x", turn_number=0)

        assert exc_info.value.metric_key == "turn.bad_json"
        assert "schema validation" in str(exc_info.value).lower()

    def test_raises_on_wrong_output_shape(self):
        """Wrong JSON shape is rejected (e.g., dict[str,int] but got str values)."""

        class _WrongShapeMetric(Metric):
            @property
            def key(self) -> str:
                return "turn.wrong_shape"

            @property
            def scope(self) -> MetricScope:
                return MetricScope.TURN

            @property
            def output_adapter(self):
                return _COUNTS_ADAPTER

            def compute(
                self, *, ctx: MetricContext, deps: MetricDeps, prior: JsonObject
            ) -> JsonValue:
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
            collector.collect_turn_metrics(run_id="run_x", turn_number=0)

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

    turn_metrics_dict = collector.collect_turn_metrics(run_id=run_id, turn_number=0)
    json.dumps(turn_metrics_dict)  # should not raise
    TurnMetrics(
        run_id=run_id,
        turn_number=0,
        metrics=turn_metrics_dict,
        created_at="2026-01-01T00:00:00",
    )

    run_metrics_dict = collector.collect_run_metrics(run_id=run_id)
    json.dumps(run_metrics_dict)  # should not raise
