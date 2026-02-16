"""Simulation run API routes."""

import asyncio
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from simulation.api.schemas.simulation import RunRequest, RunResponse
from simulation.api.services.run_execution_service import execute
from simulation.core.exceptions import SimulationRunFailure

logger = logging.getLogger(__name__)

router = APIRouter(tags=["simulation"])


@router.post(
    "/simulations/run",
    response_model=RunResponse,
    status_code=200,
    summary="Run a simulation",
    description="Execute a synchronous simulation run and return run_id, status, and likes per turn.",
)
async def post_simulations_run(
    request: Request, body: RunRequest
) -> RunResponse | Response:
    """Execute a simulation run and return completed or partial results."""
    engine = request.app.state.engine
    try:
        response = await asyncio.to_thread(
            execute,
            request=body,
            engine=engine,
        )
        return response
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
