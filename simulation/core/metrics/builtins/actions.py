from __future__ import annotations

from pydantic import TypeAdapter

from simulation.core.metrics.interfaces import (
    Metric,
    MetricContext,
    MetricDeps,
    MetricOutputAdapter,
    MetricScope,
)
from simulation.core.models.actions import TurnAction
from simulation.core.models.json_types import JsonObject, JsonValue
from simulation.core.validators import validate_run_exists

TURN_ACTION_COUNTS_BY_TYPE_ADAPTER = TypeAdapter(dict[str, int])
TURN_ACTION_TOTAL_ADAPTER = TypeAdapter(int)
RUN_ACTION_TOTALS_BY_TYPE_ADAPTER = TypeAdapter(dict[str, int])
RUN_ACTION_TOTAL_ADAPTER = TypeAdapter(int)


class TurnActionCountsByTypeMetric(Metric):
    @property
    def key(self) -> str:
        return "turn.actions.counts_by_type"

    @property
    def scope(self) -> MetricScope:
        return MetricScope.TURN

    @property
    def output_adapter(self) -> MetricOutputAdapter:
        return TURN_ACTION_COUNTS_BY_TYPE_ADAPTER

    def compute(
        self, *, ctx: MetricContext, deps: MetricDeps, prior: JsonObject
    ) -> JsonValue:
        if ctx.turn_number is None:
            raise ValueError("turn_number is required for turn metrics")

        metadata = deps.run_repo.get_turn_metadata(ctx.run_id, ctx.turn_number)
        if metadata is None:
            raise ValueError(
                f"Missing turn metadata for run_id={ctx.run_id}, turn_number={ctx.turn_number}"
            )

        ordered = sorted(metadata.total_actions.items(), key=lambda item: item[0].value)
        return {action.value: count for action, count in ordered}


class TurnActionTotalMetric(Metric):
    @property
    def key(self) -> str:
        return "turn.actions.total"

    @property
    def scope(self) -> MetricScope:
        return MetricScope.TURN

    @property
    def output_adapter(self) -> MetricOutputAdapter:
        return TURN_ACTION_TOTAL_ADAPTER

    @property
    def requires(self) -> tuple[str, ...]:
        return ("turn.actions.counts_by_type",)

    def compute(
        self, *, ctx: MetricContext, deps: MetricDeps, prior: JsonObject
    ) -> JsonValue:
        counts = prior.get("turn.actions.counts_by_type", {})
        if not isinstance(counts, dict):
            raise ValueError("turn.actions.counts_by_type must be an object")
        counts_obj: dict[str, JsonValue] = counts
        total = 0
        for key, value in counts_obj.items():
            if not isinstance(value, int):
                raise ValueError(
                    "turn.actions.counts_by_type must contain integer values "
                    f"(got {type(value).__name__} for key '{key}')"
                )
            total += value
        return total


class RunActionTotalsByTypeMetric(Metric):
    @property
    def key(self) -> str:
        return "run.actions.total_by_type"

    @property
    def scope(self) -> MetricScope:
        return MetricScope.RUN

    @property
    def output_adapter(self) -> MetricOutputAdapter:
        return RUN_ACTION_TOTALS_BY_TYPE_ADAPTER

    def compute(
        self, *, ctx: MetricContext, deps: MetricDeps, prior: JsonObject
    ) -> JsonValue:
        run = deps.run_repo.get_run(ctx.run_id)
        validate_run_exists(run=run, run_id=ctx.run_id)

        totals: dict[TurnAction, int] = {action: 0 for action in TurnAction}
        metadata_list = deps.run_repo.list_turn_metadata(ctx.run_id)
        for metadata in metadata_list:
            for action, count in metadata.total_actions.items():
                totals[action] = totals.get(action, 0) + count

        ordered = sorted(totals.items(), key=lambda item: item[0].value)
        return {action.value: count for action, count in ordered}


class RunActionTotalMetric(Metric):
    @property
    def key(self) -> str:
        return "run.actions.total"

    @property
    def scope(self) -> MetricScope:
        return MetricScope.RUN

    @property
    def output_adapter(self) -> MetricOutputAdapter:
        return RUN_ACTION_TOTAL_ADAPTER

    @property
    def requires(self) -> tuple[str, ...]:
        return ("run.actions.total_by_type",)

    def compute(
        self, *, ctx: MetricContext, deps: MetricDeps, prior: JsonObject
    ) -> JsonValue:
        totals = prior.get("run.actions.total_by_type", {})
        if not isinstance(totals, dict):
            raise ValueError("run.actions.total_by_type must be an object")
        totals_obj: dict[str, JsonValue] = totals
        total = 0
        for key, value in totals_obj.items():
            if not isinstance(value, int):
                raise ValueError(
                    "run.actions.total_by_type must contain integer values "
                    f"(got {type(value).__name__} for key '{key}')"
                )
            total += value
        return total
