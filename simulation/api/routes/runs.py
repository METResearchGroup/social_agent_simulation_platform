"""Simulation run API routes."""

import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import Response

from lib.decorators import timed
from lib.rate_limiting import limiter
from lib.request_logging import RunIdSource, log_route_completion_decorator
from simulation.api.schemas.simulation import (
    RunDetailsResponse,
    RunListItem,
    RunRequest,
    RunResponse,
    TurnSchema,
)
from simulation.api.services.run_execution_service import execute
from simulation.api.services.run_query_service import (
    get_run_details,
    get_turns_for_run,
    list_runs,
)

router = APIRouter()

RUN_ROUTE: str = "POST /v1/simulations/run"
RUNS_ROUTE: str = "GET /v1/simulations/runs"
RUN_DETAILS_ROUTE: str = "GET /v1/simulations/runs/{run_id}"
RUN_TURNS_ROUTE: str = "GET /v1/simulations/runs/{run_id}/turns"


@router.get(
    "/simulations/runs",
    response_model=list[RunListItem],
    status_code=200,
    summary="List simulation runs",
    description="Return simulation run summaries for the UI.",
)
@log_route_completion_decorator(route=RUNS_ROUTE, success_type=list)
async def get_simulation_runs(request: Request) -> list[RunListItem] | Response:
    """Return all simulation runs from the database."""
    return await _execute_get_simulation_runs(request)


@router.post(
    "/simulations/run",
    response_model=RunResponse,
    status_code=200,
    summary="Run a simulation",
    description="Execute a synchronous simulation run.",
)
@limiter.limit("5/minute")
@log_route_completion_decorator(
    route=RUN_ROUTE,
    success_type=RunResponse,
    run_id_from=RunIdSource.RESPONSE,
)
async def post_simulations_run(
    request: Request, body: RunRequest
) -> RunResponse | Response:
    """Execute a simulation run and return completed or partial results."""
    return await _execute_simulation_run(request=request, body=body)


@router.get(
    "/simulations/runs/{run_id}",
    response_model=RunDetailsResponse,
    status_code=200,
    summary="Get simulation run details",
    description="Fetch run config and turn-by-turn action summary by run ID.",
)
@log_route_completion_decorator(
    route=RUN_DETAILS_ROUTE,
    success_type=RunDetailsResponse,
    run_id_from=RunIdSource.RESPONSE,
)
async def get_simulation_run(
    request: Request, run_id: str
) -> RunDetailsResponse | Response:
    """Return run details and turn history for a persisted run."""
    return await _execute_get_simulation_run(request=request, run_id=run_id)


@router.get(
    "/simulations/runs/{run_id}/turns",
    response_model=dict[str, TurnSchema],
    status_code=200,
    summary="Get simulation run turns",
    description="Return full per-turn payload for a run ID.",
)
@log_route_completion_decorator(
    route=RUN_TURNS_ROUTE, success_type=dict, run_id_from=RunIdSource.PATH
)
async def get_simulation_run_turns(
    request: Request, run_id: str
) -> dict[str, TurnSchema] | Response:
    """Return turn payload for a run from the database."""
    return await _execute_get_simulation_run_turns(request, run_id=run_id)


@timed(attach_attr="duration_ms", log_level=None)
async def _execute_get_simulation_runs(
    request: Request,
) -> list[RunListItem] | Response:
    """Fetch run summaries from the database."""
    engine = request.app.state.deps.engine
    return await asyncio.to_thread(list_runs, engine=engine)


@timed(attach_attr="duration_ms", log_level=None)
async def _execute_simulation_run(
    request: Request, body: RunRequest
) -> RunResponse | Response:
    """Run the simulation and return response; used for timing and logging."""
    engine = request.app.state.deps.engine
    current_app_user = request.state.current_app_user
    if current_app_user is None:
        raise RuntimeError(
            "current_app_user was not set on request.state, but is required for simulation run creation."
        )
    created_by_app_user_id = current_app_user.id
    return await asyncio.to_thread(
        execute,
        request=body,
        engine=engine,
        created_by_app_user_id=created_by_app_user_id,
    )


@timed(attach_attr="duration_ms", log_level=None)
async def _execute_get_simulation_run(
    request: Request, run_id: str
) -> RunDetailsResponse | Response:
    """Fetch persisted run details and convert known failures to HTTP responses."""
    engine = request.app.state.deps.engine
    return await asyncio.to_thread(
        get_run_details,
        run_id=run_id,
        engine=engine,
    )


@timed(attach_attr="duration_ms", log_level=None)
async def _execute_get_simulation_run_turns(
    request: Request,
    run_id: str,
) -> dict[str, TurnSchema] | Response:
    """Fetch run turns and convert known failures to HTTP responses."""
    engine = request.app.state.deps.engine
    return await asyncio.to_thread(get_turns_for_run, run_id=run_id, engine=engine)
