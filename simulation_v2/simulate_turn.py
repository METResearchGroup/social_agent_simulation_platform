"""Turn simulation.

For this version, I'll decouple turn metrics generation and just generate it
after the fact. That extra complexity is obfuscating how this works.
"""

import logging

from simulation_v2.agents.actions import get_agents_actions
from simulation_v2.agents.memory.main import update_agent_memories
from simulation_v2.feeds import generate_feeds
from simulation_v2.models.feeds import GeneratedFeedsModel
from simulation_v2.models.turn import TurnInputsModel
from simulation_v2.telemetry.context import SimulationTraceContext
from simulation_v2.telemetry.opik import log_turn_llm_summary_to_opik
from simulation_v2.telemetry.simulation_metrics import log_turn_simulation_metrics

LOGGER = logging.getLogger(__name__)


def load_turn_inputs() -> TurnInputsModel:
    raise NotImplementedError("load_turn_inputs is not implemented yet")


def run_agent_actions(
    turn_inputs: TurnInputsModel,
    feeds: GeneratedFeedsModel,
    *,
    trace_ctx: SimulationTraceContext | None = None,
    turn_number: int | None = None,
):
    return get_agents_actions(
        turn_inputs,
        feeds,
        trace_ctx=trace_ctx,
        turn_number=turn_number,
    )


def mark_turn_as_done():
    pass


def simulate_turn(
    turn_inputs: TurnInputsModel,
    *,
    trace_ctx: SimulationTraceContext,
    turn_number: int,
) -> None:
    trace_ctx.turn_number = turn_number
    trace_ctx.turn_llm_collector.clear()

    LOGGER.info(
        "Generating feeds for turn %s (run_id=%s)",
        turn_number,
        trace_ctx.run_id,
    )
    feeds: GeneratedFeedsModel = generate_feeds(
        turn_inputs,
        turn_number=turn_number,
    )
    run_agent_actions(
        turn_inputs,
        feeds,
        trace_ctx=trace_ctx,
        turn_number=turn_number,
    )
    update_agent_memories()

    turn_summary = trace_ctx.turn_llm_collector.summarize(
        run_id=trace_ctx.run_id,
        turn_number=turn_number,
    )
    log_turn_llm_summary_to_opik(turn_summary)
    trace_ctx.run_llm_collector.add_turn(
        turn_summary,
        records=list(trace_ctx.turn_llm_collector.records),
    )
    log_turn_simulation_metrics(
        trace_ctx.simulation_metrics,
        run_id=trace_ctx.run_id,
        turn_number=turn_number,
    )
    trace_ctx.simulation_metrics.clear()
    mark_turn_as_done()
