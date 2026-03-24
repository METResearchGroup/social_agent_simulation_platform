"""Simulation run API routes."""

import asyncio
import logging

from fastapi import APIRouter, Request
from fastapi.responses import Response

from lib.decorators import timed
from lib.rate_limiting import limiter
from lib.request_logging import RunIdSource, log_route_completion_decorator
from simulation.api.errors import (
    ApiRunCreationFailedError,
    ApiRunForbiddenError,
    ApiRunNotFoundError,
)
from simulation.api.routes._helpers import error_response
from simulation.api.schemas.simulation import (
    RunDetailsResponse,
    RunListItem,
    RunRequest,
    RunResponse,
    TurnSchema,
)
from simulation.api.services.run_delete_service import delete_simulation_run
from simulation.api.services.run_execution_service import execute
from simulation.api.services.run_query_service import (
    get_run_details,
    get_turns_for_run,
    list_runs,
)

logger = logging.getLogger(__name__)

router = APIRouter()

RUN_ROUTE: str = "POST /v1/simulations/run"
RUNS_ROUTE: str = "GET /v1/simulations/runs"
RUN_DETAILS_ROUTE: str = "GET /v1/simulations/runs/{run_id}"
RUN_TURNS_ROUTE: str = "GET /v1/simulations/runs/{run_id}/turns"
RUN_DELETE_ROUTE: str = "DELETE /v1/simulations/runs/{run_id}"


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


@router.delete(
    "/simulations/runs/{run_id}",
    status_code=204,
    summary="Delete simulation run",
    description="Delete a persisted run and all dependent data.",
)
@log_route_completion_decorator(
    route=RUN_DELETE_ROUTE,
    success_type=type(None),
    run_id_from=RunIdSource.PATH,
)
async def delete_simulation_run_route(request: Request, run_id: str) -> Response:
    """Delete a run from storage."""
    return await _execute_delete_simulation_run(request=request, run_id=run_id)


@timed(attach_attr="duration_ms", log_level=None)
async def _execute_get_simulation_runs(
    request: Request,
) -> list[RunListItem] | Response:
    """Fetch run summaries from the database and convert failures to HTTP responses."""
    try:
        engine = request.app.state.deps.engine
        return await asyncio.to_thread(list_runs, engine=engine)
    except Exception:
        logger.exception("Unexpected error while listing simulation runs")
        return error_response(
            status_code=500,
            code="INTERNAL_ERROR",
            message="Internal server error",
            detail=None,
        )


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
    try:
        return await asyncio.to_thread(
            execute,
            request=body,
            engine=engine,
            created_by_app_user_id=created_by_app_user_id,
        )
    except ApiRunCreationFailedError as e:
        logger.exception("Simulation run failed before run creation")
        return error_response(
            status_code=500,
            code="RUN_CREATION_FAILED",
            message=e.message,
            detail=None,
        )
    except Exception:
        logger.exception("Unexpected error during simulation run")
        return error_response(
            status_code=500,
            code="INTERNAL_ERROR",
            message="Internal server error",
            detail=None,
        )


@timed(attach_attr="duration_ms", log_level=None)
async def _execute_get_simulation_run(
    request: Request, run_id: str
) -> RunDetailsResponse | Response:
    """Fetch persisted run details and convert known failures to HTTP responses."""
    engine = request.app.state.deps.engine
    try:
        return await asyncio.to_thread(
            get_run_details,
            run_id=run_id,
            engine=engine,
        )
    except ApiRunNotFoundError as e:
        return error_response(
            status_code=404,
            code="RUN_NOT_FOUND",
            message="Run not found",
            detail=e.run_id,
        )
    except ValueError as e:
        return error_response(
            status_code=400,
            code="INVALID_RUN_ID",
            message="Invalid run_id",
            detail=str(e),
        )
    except Exception:
        logger.exception("Unexpected error while fetching run details")
        return error_response(
            status_code=500,
            code="INTERNAL_ERROR",
            message="Internal server error",
            detail=None,
        )


@timed(attach_attr="duration_ms", log_level=None)
async def _execute_get_simulation_run_turns(
    request: Request,
    run_id: str,
) -> dict[str, TurnSchema] | Response:
    """Fetch run turns and convert known failures to HTTP responses."""
    try:
        engine = request.app.state.deps.engine
        return await asyncio.to_thread(get_turns_for_run, run_id=run_id, engine=engine)
    except ApiRunNotFoundError as e:
        return error_response(
            status_code=404,
            code="RUN_NOT_FOUND",
            message="Run not found",
            detail=e.run_id,
        )
    except ValueError as e:
        return error_response(
            status_code=400,
            code="INVALID_RUN_ID",
            message="Invalid run_id",
            detail=str(e),
        )
    except Exception:
        logger.exception("Unexpected error while fetching run turns")
        return error_response(
            status_code=500,
            code="INTERNAL_ERROR",
            message="Internal server error",
            detail=None,
        )


@timed(attach_attr="duration_ms", log_level=None)
async def _execute_delete_simulation_run(
    request: Request,
    run_id: str,
) -> Response:
    """Delete a persisted run and map known failures to HTTP responses."""
    engine = request.app.state.deps.engine
    current_app_user = request.state.current_app_user
    if current_app_user is None:
        raise RuntimeError(
            "current_app_user was not set on request.state, but is required for delete run."
        )
    try:
        await asyncio.to_thread(
            delete_simulation_run,
            run_id=run_id,
            engine=engine,
            current_app_user_id=current_app_user.id,
        )
        return Response(status_code=204)
    except ApiRunNotFoundError as e:
        return error_response(
            status_code=404,
            code="RUN_NOT_FOUND",
            message="Run not found",
            detail=e.run_id,
        )
    except ApiRunForbiddenError as e:
        return error_response(
            status_code=403,
            code="RUN_FORBIDDEN",
            message="Not allowed to delete this run",
            detail=e.run_id,
        )
    except ValueError as e:
        return error_response(
            status_code=400,
            code="INVALID_RUN_ID",
            message="Invalid run_id",
            detail=str(e),
        )
    except Exception:
        logger.exception("Unexpected error while deleting simulation run")
        return error_response(
            status_code=500,
            code="INTERNAL_ERROR",
            message="Internal server error",
            detail=None,
        )
