"""Orchestrates simulation run execution and builds API response DTOs."""

from collections.abc import Iterable

from lib.timestamp_utils import get_current_timestamp
from simulation.api.schemas.simulation import (
    ErrorDetail,
    RunRequest,
    RunResponse,
    RunResponseStatus,
    TurnSummaryItem,
)
from simulation.core.engine import SimulationEngine
from simulation.core.exceptions import InconsistentTurnDataError, SimulationRunFailure
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
        _validate_turn_data_consistency(
            metadata_list=metadata_list,
            turn_metrics_list=turn_metrics_list,
        )
        run_metrics = engine.get_run_metrics(e.run_id)
        turns = _build_turn_summaries(
            metadata_list=metadata_list,
            turn_metrics_list=turn_metrics_list,
        )
        failed_run = engine.get_run(e.run_id)
        created_at = (
            failed_run.created_at if failed_run is not None else get_current_timestamp()
        )
        return RunResponse(
            run_id=e.run_id,
            created_at=created_at,
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
    _validate_turn_data_consistency(
        metadata_list=metadata_list,
        turn_metrics_list=turn_metrics_list,
    )
    run_metrics: RunMetrics | None = engine.get_run_metrics(run.run_id)
    turns: list[TurnSummaryItem] = _build_turn_summaries(
        metadata_list=metadata_list,
        turn_metrics_list=turn_metrics_list,
    )
    return RunResponse(
        run_id=run.run_id,
        created_at=run.created_at,
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


def _validate_turn_data_consistency(
    *,
    metadata_list: Iterable[TurnMetadata],
    turn_metrics_list: Iterable[TurnMetrics],
) -> None:
    """Raise if metadata and metrics have different sets of turn numbers."""
    metadata_turn_numbers: set[int] = {m.turn_number for m in metadata_list}
    metrics_turn_numbers: set[int] = {t.turn_number for t in turn_metrics_list}
    _assert_turn_sets_match(
        metadata_turns=metadata_turn_numbers,
        metrics_turns=metrics_turn_numbers,
    )


def _build_turn_summaries(
    *,
    metadata_list: Iterable[TurnMetadata],
    turn_metrics_list: Iterable[TurnMetrics],
) -> list[TurnSummaryItem]:
    """Build deterministic turn summaries by turn_number.

    Callers must pass lists such that every turn number present in one list
    is present in the other. The function validates and raises
    InconsistentTurnDataError if not.
    """
    metadata_by_turn: dict[int, TurnMetadata] = {
        item.turn_number: item for item in metadata_list
    }
    metrics_by_turn: dict[int, TurnMetrics] = {
        item.turn_number: item for item in turn_metrics_list
    }
    metadata_turns: set[int] = set(metadata_by_turn.keys())
    metrics_turns: set[int] = set(metrics_by_turn.keys())
    _assert_turn_sets_match(
        metadata_turns=metadata_turns,
        metrics_turns=metrics_turns,
    )
    turns: list[TurnSummaryItem] = []
    for turn_number in sorted(metadata_turns):
        metadata = metadata_by_turn[turn_number]
        metrics = metrics_by_turn[turn_number]
        turns.append(
            TurnSummaryItem(
                turn_number=turn_number,
                created_at=metadata.created_at,
                total_actions={k.value: v for k, v in metadata.total_actions.items()},
                metrics=metrics.metrics,
            )
        )
    return turns


def _assert_turn_sets_match(
    *,
    metadata_turns: set[int],
    metrics_turns: set[int],
) -> None:
    """Raise InconsistentTurnDataError if the two turn-number sets differ."""
    if metadata_turns != metrics_turns:
        metadata_only = metadata_turns - metrics_turns
        metrics_only = metrics_turns - metadata_turns
        raise InconsistentTurnDataError(
            (
                "Turn metadata and turn metrics have different turn number sets: "
                f"metadata_only={sorted(metadata_only)}, metrics_only={sorted(metrics_only)}"
            ),
            metadata_only=metadata_only,
            metrics_only=metrics_only,
        )
