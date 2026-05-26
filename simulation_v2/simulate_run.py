import logging
import uuid

from simulation_v2.lib.decorators import iteration_log_level, progress_items
from simulation_v2.models.turn import TurnInputsModel
from simulation_v2.simulate_turn import simulate_turn
from simulation_v2.telemetry.context import SimulationTraceContext
from simulation_v2.telemetry.opik import (
    configure_opik,
    flush_opik,
    is_opik_enabled,
    log_run_llm_summary_to_opik,
)

LOGGER = logging.getLogger(__name__)


def simulate_run(turn_inputs: TurnInputsModel) -> str:
    """Run the simulation for all turns. Returns the run_id."""
    run_id = str(uuid.uuid4())
    configure_opik()
    trace_ctx = SimulationTraceContext(run_id=run_id, enabled=is_opik_enabled())
    user_count = len(turn_inputs.seed_data.users)

    LOGGER.info(
        "Starting simulation run_id=%s users=%s turns=%s opik_enabled=%s",
        run_id,
        user_count,
        turn_inputs.total_turns,
        trace_ctx.enabled,
    )

    for i in progress_items(
        range(turn_inputs.total_turns),
        desc="Simulation run (turns)",
        unit="turn",
    ):
        turn_number = i + 1
        LOGGER.log(
            iteration_log_level(),
            "Starting turn %s/%s for run_id=%s",
            turn_number,
            turn_inputs.total_turns,
            run_id,
        )
        simulate_turn(
            turn_inputs,
            trace_ctx=trace_ctx,
            turn_number=turn_number,
        )
        LOGGER.log(
            iteration_log_level(),
            "Finished turn %s/%s for run_id=%s",
            turn_number,
            turn_inputs.total_turns,
            run_id,
        )

    log_run_llm_summary_to_opik(
        trace_ctx.run_llm_collector.summarize(
            run_id=run_id,
            total_turns=turn_inputs.total_turns,
        )
    )
    flush_opik()
    LOGGER.info("Simulation complete run_id=%s", run_id)
    return run_id
