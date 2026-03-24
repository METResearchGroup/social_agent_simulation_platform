"""Delete persisted simulation run (API layer)."""

from __future__ import annotations

from simulation.api.errors import ApiRunForbiddenError, ApiRunNotFoundError
from simulation.core.engine import SimulationEngine
from simulation.core.utils.exceptions import RunNotFoundError
from simulation.core.utils.validators import validate_run_id


def delete_simulation_run(
    *,
    run_id: str,
    engine: SimulationEngine,
    current_app_user_id: str | None,
) -> None:
    """Load the run, enforce ownership when attributed, then delete from SQLite.

    Raises:
        ApiRunNotFoundError: If the run does not exist
        ApiRunForbiddenError: If ``runs.app_user_id`` is set and does not match
            ``current_app_user_id``
        ValueError: If ``run_id`` is invalid (caller maps to HTTP 400)
    """
    validated = validate_run_id(run_id)
    run = engine.get_run(validated)
    if run is None:
        raise ApiRunNotFoundError(validated)
    if run.app_user_id is not None and run.app_user_id != current_app_user_id:
        raise ApiRunForbiddenError(validated)
    try:
        engine.delete_run(validated)
    except RunNotFoundError:
        raise ApiRunNotFoundError(validated) from None
