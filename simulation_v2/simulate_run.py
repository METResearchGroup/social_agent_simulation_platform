import logging
import uuid

from tqdm import tqdm

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

_TQDM_BAR_FORMAT = "{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"


def simulate_run(turn_inputs: TurnInputsModel, *, show_progress: bool = True) -> str:
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

    turn_iter = range(turn_inputs.total_turns)
    if show_progress:
        turn_iter = tqdm(
            turn_iter,
            desc="Simulation run (turns)",
            unit="turn",
            total=turn_inputs.total_turns,
            bar_format=_TQDM_BAR_FORMAT,
        )

    for i in turn_iter:
        turn_number = i + 1
        log = LOGGER.debug if show_progress else LOGGER.info
        log(
            "Starting turn %s/%s for run_id=%s",
            turn_number,
            turn_inputs.total_turns,
            run_id,
        )
        simulate_turn(
            turn_inputs,
            trace_ctx=trace_ctx,
            turn_number=turn_number,
            show_progress=show_progress,
        )
        log(
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
