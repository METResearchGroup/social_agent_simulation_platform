"""Simulation trace context for simulation v2 telemetry."""

from __future__ import annotations

from dataclasses import dataclass, field

from simulation_v2.telemetry.llm_collector import (
    RunLlmMetricsCollector,
    TurnLlmMetricsCollector,
)


@dataclass
class SimulationTraceContext:
    run_id: str
    turn_number: int = 0
    enabled: bool = True
    turn_llm_collector: TurnLlmMetricsCollector = field(
        default_factory=TurnLlmMetricsCollector
    )
    run_llm_collector: RunLlmMetricsCollector = field(
        default_factory=RunLlmMetricsCollector
    )
