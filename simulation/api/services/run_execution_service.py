"""Orchestrates simulation run execution and builds API response DTOs."""

from simulation.api.schemas.simulation import (
    ErrorDetail,
    LikesPerTurnItem,
    RunRequest,
    RunResponse,
)
from simulation.core.engine import SimulationEngine
from simulation.core.exceptions import SimulationRunFailure
from simulation.core.models.actions import TurnAction
from simulation.core.models.runs import RunConfig
from simulation.core.models.turns import TurnMetadata


def _build_likes_per_turn_from_metadata(
    metadata_list: list[TurnMetadata],
) -> tuple[list[LikesPerTurnItem], int]:
    """Derive likes_per_turn and total_likes from turn metadata list."""
    likes_per_turn = [
        LikesPerTurnItem(
            turn_number=tm.turn_number,
            likes=tm.total_actions.get(TurnAction.LIKE, 0),
        )
        for tm in metadata_list
    ]
    total_likes = sum(item.likes for item in likes_per_turn)
    return likes_per_turn, total_likes


def _build_run_config(request: RunRequest) -> RunConfig:
    """Build RunConfig from request, applying API defaults."""
    return RunConfig(
        num_agents=request.num_agents,
        num_turns=request.num_turns if request.num_turns is not None else 10,
        feed_algorithm=request.feed_algorithm or "chronological",
    )


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
    run_config = _build_run_config(request=request)
    try:
        run = engine.execute_run(run_config=run_config)
    except SimulationRunFailure as e:
        if e.run_id is None:
            raise
        metadata_list = engine.list_turn_metadata(e.run_id)
        likes_per_turn, total_likes = _build_likes_per_turn_from_metadata(metadata_list)
        detail = str(e.cause) if e.cause else None
        return RunResponse(
            run_id=e.run_id,
            status="failed",
            num_agents=run_config.num_agents,
            num_turns=run_config.num_turns,
            likes_per_turn=likes_per_turn,
            total_likes=total_likes,
            error=ErrorDetail(
                code="SIMULATION_FAILED",
                message=e.args[0] if e.args else "Run failed during execution",
                detail=detail,
            ),
        )
    metadata_list = engine.list_turn_metadata(run.run_id)
    likes_per_turn, total_likes = _build_likes_per_turn_from_metadata(metadata_list)
    return RunResponse(
        run_id=run.run_id,
        status="completed",
        num_agents=run.total_agents,
        num_turns=run.total_turns,
        likes_per_turn=likes_per_turn,
        total_likes=total_likes,
        error=None,
    )
