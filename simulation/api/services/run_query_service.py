"""Read-side CQRS service for simulation run lookup APIs."""

from simulation.api.dummy_data import DUMMY_RUNS, DUMMY_TURNS
from simulation.api.schemas.simulation import (
    RunConfigDetail,
    RunDetailsResponse,
    RunListItem,
    TurnActionsItem,
    TurnSchema,
)
from simulation.core.engine import SimulationEngine
from simulation.core.exceptions import RunNotFoundError
from simulation.core.models.turns import TurnMetadata
from simulation.core.validators import validate_run_exists, validate_run_id


def list_runs_dummy() -> list[RunListItem]:
    """Return deterministic dummy run list for UI integration."""
    return sorted(
        DUMMY_RUNS,
        key=lambda run: run.created_at,
        reverse=True,
    )


def get_turns_for_run_dummy(*, run_id: str) -> dict[str, TurnSchema]:
    """Return deterministic dummy turns for a run ID."""
    validated_run_id: str = validate_run_id(run_id)
    turns: dict[str, TurnSchema] | None = DUMMY_TURNS.get(validated_run_id)
    if turns is None:
        raise RunNotFoundError(validated_run_id)
    return dict(sorted(turns.items(), key=lambda item: int(item[0])))


def get_run_details(*, run_id: str, engine: SimulationEngine) -> RunDetailsResponse:
    """Build run-details response for a persisted run.

    Args:
        run_id: Identifier for the run.
        engine: Simulation engine exposing read/query methods.

    Returns:
        RunDetailsResponse with run config and ordered turn summaries.

    Raises:
        ValueError: If run_id is empty.
        RunNotFoundError: If the run does not exist.
    """
    validated_run_id: str = validate_run_id(run_id)
    run = engine.get_run(validated_run_id)
    run = validate_run_exists(run=run, run_id=validated_run_id)

    metadata_list: list[TurnMetadata] = engine.list_turn_metadata(validated_run_id)
    turns: list[TurnActionsItem] = _build_turn_actions_items(
        metadata_list=metadata_list
    )

    return RunDetailsResponse(
        run_id=run.run_id,
        status=run.status,
        created_at=run.created_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
        config=RunConfigDetail(
            num_agents=run.total_agents,
            num_turns=run.total_turns,
            feed_algorithm=run.feed_algorithm,
        ),
        turns=turns,
    )


def _build_turn_actions_items(
    *, metadata_list: list[TurnMetadata]
) -> list[TurnActionsItem]:
    """Map turn metadata to deterministic, API-serializable turn summaries."""
    sorted_metadata: list[TurnMetadata] = sorted(
        metadata_list,
        key=lambda item: item.turn_number,
    )
    return [
        TurnActionsItem(
            turn_number=item.turn_number,
            created_at=item.created_at,
            total_actions={
                action.value: count for action, count in item.total_actions.items()
            },
        )
        for item in sorted_metadata
    ]
