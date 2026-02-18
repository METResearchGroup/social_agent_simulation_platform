"""Orchestrates simulation run execution and builds API response DTOs."""

from collections.abc import Iterable

from simulation.api.schemas.simulation import (
    ErrorDetail,
    RunRequest,
    RunResponse,
    RunResponseStatus,
    TurnSummaryItem,
)
from simulation.core.engine import SimulationEngine
from simulation.core.exceptions import SimulationRunFailure
from simulation.core.models.metrics import RunMetrics, TurnMetrics
from simulation.core.models.runs import Run, RunConfig
from simulation.core.models.turns import TurnMetadata

DEFAULT_NUM_TURNS: int = 10
DEFAULT_FEED_ALGORITHM: str = "chronological"


def execute(
    request: RunRequest,
    engine: SimulationEngine,
) -> RunResponse:
    """Execute a simulation run and return the API response.

    Builds RunConfig with API defaults, runs the engine synchronously,
    then builds RunResponse from the run and persisted turn metadata.
    On SimulationRunFailure with run_id, returns 200 with partial results
    and error payload; callers should return 500 for run_id=None or other
    exceptions.
    """
    run_config: RunConfig = _build_run_config(request=request)
    try:
        run: Run = engine.execute_run(run_config=run_config)
    except SimulationRunFailure as e:
        if e.run_id is None:
            raise
        metadata_list = engine.list_turn_metadata(e.run_id)
        turn_metrics_list = engine.list_turn_metrics(e.run_id)
        run_metrics = engine.get_run_metrics(e.run_id)
        turns: list[TurnSummaryItem] = _build_turn_summaries(
            metadata_list=metadata_list,
            turn_metrics_list=turn_metrics_list,
        )
        return RunResponse(
            run_id=e.run_id,
            status=RunResponseStatus.FAILED,
            num_agents=run_config.num_agents,
            num_turns=run_config.num_turns,
            turns=turns,
            run_metrics=run_metrics.metrics if run_metrics else None,
            error=ErrorDetail(
                code="SIMULATION_FAILED",
                message=e.args[0] if e.args else "Run failed during execution",
                detail=None,
            ),
        )
    metadata_list: list[TurnMetadata] = engine.list_turn_metadata(run.run_id)
    turn_metrics_list: list[TurnMetrics] = engine.list_turn_metrics(run.run_id)
    run_metrics: RunMetrics | None = engine.get_run_metrics(run.run_id)
    turns: list[TurnSummaryItem] = _build_turn_summaries(
        metadata_list=metadata_list,
        turn_metrics_list=turn_metrics_list,
    )
    return RunResponse(
        run_id=run.run_id,
        status=RunResponseStatus.COMPLETED,
        num_agents=run.total_agents,
        num_turns=run.total_turns,
        turns=turns,
        run_metrics=run_metrics.metrics if run_metrics else None,
        error=None,
    )


def _build_run_config(request: RunRequest) -> RunConfig:
    """Build RunConfig from request, applying API defaults."""
    return RunConfig(
        num_agents=request.num_agents,
        num_turns=request.num_turns
        if request.num_turns is not None
        else DEFAULT_NUM_TURNS,
        feed_algorithm=request.feed_algorithm or DEFAULT_FEED_ALGORITHM,
    )


def _build_turn_summaries(
    *,
    metadata_list: Iterable[TurnMetadata],
    turn_metrics_list: Iterable[TurnMetrics],
) -> list[TurnSummaryItem]:
    """Build deterministic turn summaries by turn_number."""
    metadata_by_turn: dict[int, TurnMetadata] = {
        item.turn_number: item for item in metadata_list
    }
    metrics_by_turn: dict[int, TurnMetrics] = {
        item.turn_number: item for item in turn_metrics_list
    }

    all_turn_numbers = sorted(
        set(metadata_by_turn.keys()) | set(metrics_by_turn.keys())
    )
    turns: list[TurnSummaryItem] = []
    for turn_number in all_turn_numbers:
        metadata = metadata_by_turn.get(turn_number)
        metrics = metrics_by_turn.get(turn_number)
        if metadata is None or metrics is None:
            # Incomplete turn: return partial state without computed metrics.
            continue
        turns.append(
            TurnSummaryItem(
                turn_number=turn_number,
                created_at=metadata.created_at,
                total_actions={k.value: v for k, v in metadata.total_actions.items()},
                metrics=metrics.metrics,
            )
        )
    return turns
