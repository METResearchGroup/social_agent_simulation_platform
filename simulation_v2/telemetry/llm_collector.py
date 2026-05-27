"""In-process LLM call metrics collection for simulation v2."""

from __future__ import annotations

from dataclasses import dataclass, field

from simulation_v2.telemetry.models import (
    ActionLlmMetricsSummary,
    ActionType,
    LatencyPercentiles,
    RunLlmMetricsSummary,
    TurnLlmMetricsSummary,
)

_ACTION_TYPES: tuple[ActionType, ...] = (
    "like_posts",
    "write_post",
    "follow_users",
    "comment_on_post",
)


@dataclass
class LlmCallRecord:
    run_id: str
    turn_number: int
    user_id: str
    action_type: ActionType
    latency_ms: float
    cost_usd: float | None
    prompt_tokens: int | None
    completion_tokens: int | None
    success: bool
    error_type: str | None = None
    write_attempt_index: int | None = None


def compute_percentiles(latencies: list[float]) -> LatencyPercentiles:
    """Compute p50/p90/p99 from sorted latencies. Omits p99 when N < 30."""
    if not latencies:
        return LatencyPercentiles(p50=0.0, p90=0.0, p99=None)

    sorted_latencies = sorted(latencies)
    n = len(sorted_latencies)

    def _value_at_percentile(p: float) -> float:
        index = min(max(int(n * p / 100) - 1, 0), n - 1)
        return sorted_latencies[index]

    p99 = _value_at_percentile(99) if n >= 30 else None
    return LatencyPercentiles(
        p50=_value_at_percentile(50),
        p90=_value_at_percentile(90),
        p99=p99,
    )


def _summarize_records(records: list[LlmCallRecord]) -> ActionLlmMetricsSummary:
    latencies = [record.latency_ms for record in records]
    total_cost = sum(record.cost_usd or 0.0 for record in records)
    return ActionLlmMetricsSummary(
        request_count=len(records),
        total_cost_usd=total_cost,
        latency_ms=compute_percentiles(latencies),
    )


def _empty_action_summary() -> ActionLlmMetricsSummary:
    return ActionLlmMetricsSummary(
        request_count=0,
        total_cost_usd=0.0,
        latency_ms=LatencyPercentiles(p50=0.0, p90=0.0, p99=None),
    )


@dataclass
class TurnLlmMetricsCollector:
    records: list[LlmCallRecord] = field(default_factory=list)

    def add(self, record: LlmCallRecord) -> None:
        self.records.append(record)

    def clear(self) -> None:
        self.records.clear()

    def summarize(self, *, run_id: str, turn_number: int) -> TurnLlmMetricsSummary:
        by_action: dict[ActionType, ActionLlmMetricsSummary] = {}
        for action_type in _ACTION_TYPES:
            action_records = [
                record for record in self.records if record.action_type == action_type
            ]
            by_action[action_type] = (
                _summarize_records(action_records)
                if action_records
                else _empty_action_summary()
            )
        return TurnLlmMetricsSummary(
            turn_number=turn_number,
            run_id=run_id,
            by_action=by_action,
            overall=_summarize_records(self.records),
        )


@dataclass
class RunLlmMetricsCollector:
    turn_summaries: list[TurnLlmMetricsSummary] = field(default_factory=list)
    records: list[LlmCallRecord] = field(default_factory=list)

    def add_turn(
        self,
        summary: TurnLlmMetricsSummary,
        *,
        records: list[LlmCallRecord] | None = None,
    ) -> None:
        self.turn_summaries.append(summary)
        if records:
            self.records.extend(records)

    def summarize(self, *, run_id: str, total_turns: int) -> RunLlmMetricsSummary:
        return RunLlmMetricsSummary(
            run_id=run_id,
            total_turns=total_turns,
            by_turn=list(self.turn_summaries),
            overall=_summarize_records(self.records),
        )
