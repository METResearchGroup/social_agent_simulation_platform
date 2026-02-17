"""Simulation run API routes."""

import asyncio
import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from lib.decorators import timed
from lib.request_logging import log_route_completion
from simulation.api.schemas.simulation import (
    RunDetailsResponse,
    RunRequest,
    RunResponse,
)
from simulation.api.services.run_execution_service import execute
from simulation.api.services.run_query_service import get_run_details
from simulation.core.exceptions import RunNotFoundError, SimulationRunFailure

logger = logging.getLogger(__name__)

router = APIRouter(tags=["simulation"])

SIMULATION_RUN_ROUTE: str = "POST /v1/simulations/run"
SIMULATION_RUN_DETAILS_ROUTE: str = "GET /v1/simulations/runs/{run_id}"


@router.post(
    "/simulations/run",
    response_model=RunResponse,
    status_code=200,
    summary="Run a simulation",
    description="Execute a synchronous simulation run.",
)
async def post_simulations_run(
    request: Request, body: RunRequest
) -> RunResponse | Response:
    """Execute a simulation run and return completed or partial results."""
    response = await _execute_simulation_run(request=request, body=body)
    request_id = getattr(request.state, "request_id", "")
    latency_ms = getattr(request.state, "duration_ms", 0)
    if isinstance(response, RunResponse):
        log_route_completion(
            request_id=request_id,
            route=SIMULATION_RUN_ROUTE,
            latency_ms=latency_ms,
            run_id=response.run_id,
            status=response.status.value,
            error_code=response.error.code if response.error else None,
        )
    else:
        error_code = _error_code_from_json_response(response)
        log_route_completion(
            request_id=request_id,
            route=SIMULATION_RUN_ROUTE,
            latency_ms=latency_ms,
            run_id=None,
            status=str(response.status_code),
            error_code=error_code,
        )
    return response


@router.get(
    "/simulations/runs/{run_id}",
    response_model=RunDetailsResponse,
    status_code=200,
    summary="Get simulation run details",
    description="Fetch run config and turn-by-turn action summary by run ID.",
)
async def get_simulation_run(
    request: Request, run_id: str
) -> RunDetailsResponse | Response:
    """Return run details and turn history for a persisted run."""
    response = await _execute_get_simulation_run(request=request, run_id=run_id)
    request_id = getattr(request.state, "request_id", "")
    latency_ms = getattr(request.state, "duration_ms", 0)
    if isinstance(response, RunDetailsResponse):
        log_route_completion(
            request_id=request_id,
            route=SIMULATION_RUN_DETAILS_ROUTE,
            latency_ms=latency_ms,
            run_id=response.run_id,
            status=response.status.value,
            error_code=None,
        )
    else:
        error_code = _error_code_from_json_response(response)
        log_route_completion(
            request_id=request_id,
            route=SIMULATION_RUN_DETAILS_ROUTE,
            latency_ms=latency_ms,
            run_id=run_id,
            status=str(response.status_code),
            error_code=error_code,
        )
    return response


@timed(attach_attr="duration_ms", log_level=None)
async def _execute_simulation_run(
    request: Request, body: RunRequest
) -> RunResponse | Response:
    """Run the simulation and return response; used for timing and logging."""
    engine = request.app.state.engine
    try:
        return await asyncio.to_thread(
            execute,
            request=body,
            engine=engine,
        )
    except SimulationRunFailure as e:
        logger.exception("Simulation run failed before run creation")
        return _error_response(
            status_code=500,
            code="RUN_CREATION_FAILED",
            message=e.args[0] if e.args else "Run creation or status update failed",
            detail=str(e.cause) if e.cause else None,
        )
    except Exception:
        logger.exception("Unexpected error during simulation run")
        return _error_response(
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
    engine = request.app.state.engine
    try:
        return await asyncio.to_thread(
            get_run_details,
            run_id=run_id,
            engine=engine,
        )
    except RunNotFoundError as e:
        return _error_response(
            status_code=404,
            code="RUN_NOT_FOUND",
            message="Run not found",
            detail=e.run_id,
        )
    except ValueError as e:
        return _error_response(
            status_code=400,
            code="INVALID_RUN_ID",
            message="Invalid run_id",
            detail=str(e),
        )
    except Exception:
        logger.exception("Unexpected error while fetching run details")
        return _error_response(
            status_code=500,
            code="INTERNAL_ERROR",
            message="Internal server error",
            detail=None,
        )


def _error_code_from_json_response(response: Response) -> str | None:
    """Extract error code from JSONResponse content if present."""
    content = getattr(response, "content", None)
    if isinstance(content, dict):
        return content.get("error", {}).get("code")
    if hasattr(response, "body") and response.body:
        try:
            raw = response.body
            if isinstance(raw, bytes):
                raw = raw.decode()
            else:
                raw = bytes(raw).decode()
            data = json.loads(raw)
            return data.get("error", {}).get("code")
        except (TypeError, ValueError):
            return None
    return None


def _error_response(
    status_code: int,
    code: str,
    message: str,
    detail: str | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "detail": detail,
            }
        },
    )
