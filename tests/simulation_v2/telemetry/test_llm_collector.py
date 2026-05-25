"""Tests for simulation v2 LLM metrics collectors."""

from __future__ import annotations

from simulation_v2.telemetry.llm_collector import (
    LlmCallRecord,
    TurnLlmMetricsCollector,
    compute_percentiles,
)


def _record(
    *,
    action_type: str = "like_posts",
    latency_ms: float = 100.0,
    cost_usd: float = 0.01,
) -> LlmCallRecord:
    return LlmCallRecord(
        run_id="run-1",
        turn_number=1,
        user_id="user-1",
        action_type=action_type,  # type: ignore[arg-type]
        latency_ms=latency_ms,
        cost_usd=cost_usd,
        prompt_tokens=10,
        completion_tokens=5,
        success=True,
    )


class TestLlmCollector:
    def test_compute_percentiles_with_hundred_values(self) -> None:
        latencies = [float(i) for i in range(1, 101)]

        percentiles = compute_percentiles(latencies)

        assert percentiles.p50 == 50.0
        assert percentiles.p90 == 90.0
        assert percentiles.p99 == 99.0

    def test_compute_percentiles_omits_p99_when_sample_size_below_30(self) -> None:
        latencies = [float(i) for i in range(1, 30)]

        percentiles = compute_percentiles(latencies)

        assert percentiles.p50 == 14.0
        assert percentiles.p90 == 26.0
        assert percentiles.p99 is None

    def test_turn_collector_summarize_groups_by_action_and_sums_cost(self) -> None:
        collector = TurnLlmMetricsCollector()
        collector.add(
            _record(action_type="like_posts", latency_ms=100.0, cost_usd=0.01)
        )
        collector.add(
            _record(action_type="like_posts", latency_ms=200.0, cost_usd=0.02)
        )
        collector.add(
            _record(action_type="follow_users", latency_ms=300.0, cost_usd=0.03)
        )

        summary = collector.summarize(run_id="run-1", turn_number=1)

        assert summary.by_action["like_posts"].request_count == 2
        assert summary.by_action["like_posts"].total_cost_usd == 0.03
        assert summary.by_action["follow_users"].request_count == 1
        assert summary.by_action["write_post"].request_count == 0
        assert summary.overall.request_count == 3
        assert summary.overall.total_cost_usd == 0.06
