"""Non-Opik simulation outcome metrics for simulation v2."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from simulation_v2.models.telemetry import ActionType

if TYPE_CHECKING:
    from simulation_v2.telemetry.context import SimulationTraceContext

LOGGER = logging.getLogger("simulation_v2.simulation_metrics")


@dataclass
class SimulationOutcomeRecord:
    turn_number: int
    user_id: str
    action_type: ActionType
    llm_proposed_count: int
    kept_count: int


@dataclass
class SimulationMetricsCollector:
    records: list[SimulationOutcomeRecord] = field(default_factory=list)

    def record(
        self,
        *,
        turn_number: int,
        user_id: str,
        action_type: ActionType,
        llm_proposed_count: int,
        kept_count: int,
    ) -> None:
        self.records.append(
            SimulationOutcomeRecord(
                turn_number=turn_number,
                user_id=user_id,
                action_type=action_type,
                llm_proposed_count=llm_proposed_count,
                kept_count=kept_count,
            )
        )

    def clear(self) -> None:
        self.records.clear()


def record_stochastic_filter(
    *,
    action_type: ActionType,
    user_id: str,
    proposed: int,
    kept: int,
    trace_ctx: SimulationTraceContext,
) -> None:
    """Record proposed vs kept counts for a stochastic filter outcome."""
    trace_ctx.simulation_metrics.record(
        turn_number=trace_ctx.turn_number,
        user_id=user_id,
        action_type=action_type,
        llm_proposed_count=proposed,
        kept_count=kept,
    )


def log_turn_simulation_metrics(
    collector: SimulationMetricsCollector,
    *,
    run_id: str,
    turn_number: int,
) -> None:
    """Emit one JSON log line per simulation outcome record."""
    for record in collector.records:
        payload = {
            "run_id": run_id,
            "turn_number": turn_number,
            "user_id": record.user_id,
            "action_type": record.action_type,
            "llm_proposed_count": record.llm_proposed_count,
            "kept_count": record.kept_count,
        }
        LOGGER.info(json.dumps(payload))
