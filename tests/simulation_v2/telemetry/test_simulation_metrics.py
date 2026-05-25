"""Tests for simulation v2 simulation outcome metrics."""

from __future__ import annotations

from simulation_v2.telemetry.simulation_metrics import SimulationMetricsCollector


class TestSimulationMetrics:
    def test_simulation_metrics_collector_record_and_clear(self) -> None:
        collector = SimulationMetricsCollector()
        collector.record(
            turn_number=1,
            user_id="user-1",
            action_type="like_posts",
            llm_proposed_count=3,
            kept_count=1,
        )

        assert len(collector.records) == 1
        assert collector.records[0].llm_proposed_count == 3
        assert collector.records[0].kept_count == 1

        collector.clear()
        assert collector.records == []
