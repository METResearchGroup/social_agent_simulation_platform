"""Simulation run API routes."""

import asyncio
import logging

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, Response

from lib.decorators import timed
from lib.rate_limiting import RATE_LIMIT_AGENTS_CREATE, limiter
from lib.request_logging import RunIdSource, log_route_completion_decorator
from simulation.api.constants import (
    DEFAULT_AGENT_LIST_LIMIT,
    DEFAULT_AGENT_LIST_OFFSET,
    DEFAULT_SIMULATION_CONFIG,
    MAX_AGENT_LIST_LIMIT,
)
from simulation.api.dependencies.auth import require_auth
from simulation.api.errors import (
    ApiHandleAlreadyExistsError,
    ApiRunCreationFailedError,
    ApiRunNotFoundError,
)
from simulation.api.schemas.simulation import (
    AgentSchema,
    CreateAgentRequest,
    DefaultConfigSchema,
    FeedAlgorithmSchema,
    MetricSchema,
    PostSchema,
    RunDetailsResponse,
    RunListItem,
    RunRequest,
    RunResponse,
    TurnSchema,
)
from simulation.api.services.agent_command_service import create_agent
from simulation.api.services.agent_query_service import list_agents
from simulation.api.services.metadata_service import list_feed_algorithms, list_metrics
from simulation.api.services.run_execution_service import execute
from simulation.api.services.run_query_service import (
    get_posts_by_uris,
    get_run_details,
    get_turns_for_run,
    list_runs,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["simulation"], dependencies=[Depends(require_auth)])

SIMULATION_RUN_ROUTE: str = "POST /v1/simulations/run"
SIMULATION_RUNS_ROUTE: str = "GET /v1/simulations/runs"
SIMULATION_RUN_DETAILS_ROUTE: str = "GET /v1/simulations/runs/{run_id}"
SIMULATION_RUN_TURNS_ROUTE: str = "GET /v1/simulations/runs/{run_id}/turns"
SIMULATION_AGENTS_ROUTE: str = "GET /v1/simulations/agents"
SIMULATION_AGENTS_CREATE_ROUTE: str = "POST /v1/simulations/agents"
SIMULATION_POSTS_ROUTE: str = "GET /v1/simulations/posts"
SIMULATION_FEED_ALGORITHMS_ROUTE: str = "GET /v1/simulations/feed-algorithms"
SIMULATION_METRICS_ROUTE: str = "GET /v1/simulations/metrics"
SIMULATION_CONFIG_DEFAULT_ROUTE: str = "GET /v1/simulations/config/default"


@router.get(
    "/simulations/feed-algorithms",
    response_model=list[FeedAlgorithmSchema],
    status_code=200,
    summary="List feed algorithms",
    description="Return available feed algorithms with metadata for the UI.",
)
@log_route_completion_decorator(
    route=SIMULATION_FEED_ALGORITHMS_ROUTE, success_type=list
)
async def get_simulation_feed_algorithms(
    request: Request,
) -> list[FeedAlgorithmSchema] | Response:
    """Return registered feed algorithms with metadata."""
    return await _execute_get_feed_algorithms(request)


@router.get(
    "/simulations/metrics",
    response_model=list[MetricSchema],
    status_code=200,
    summary="List metrics",
    description="Return available metrics with metadata for the UI.",
)
@log_route_completion_decorator(route=SIMULATION_METRICS_ROUTE, success_type=list)
async def get_simulation_metrics(
    request: Request,
) -> list[MetricSchema] | Response:
    """Return registered metrics with metadata."""
    return await _execute_get_metrics(request)


@router.get(
    "/simulations/config/default",
    response_model=DefaultConfigSchema,
    status_code=200,
    summary="Get default simulation config",
    description="Return default config for simulation start form (num_agents, num_turns, metric_keys).",
)
@log_route_completion_decorator(
    route=SIMULATION_CONFIG_DEFAULT_ROUTE, success_type=DefaultConfigSchema
)
async def get_simulation_config_default(
    request: Request,
) -> DefaultConfigSchema | Response:
    """Return default config for simulation start form."""
    return await _execute_get_default_config(request)


@router.post(
    "/simulations/agents",
    response_model=AgentSchema,
    status_code=201,
    summary="Create simulation agent",
    description="Create a user-generated agent.",
)
@limiter.limit(RATE_LIMIT_AGENTS_CREATE)
@log_route_completion_decorator(
    route=SIMULATION_AGENTS_CREATE_ROUTE, success_type=AgentSchema
)
async def post_simulation_agents(
    request: Request, body: CreateAgentRequest
) -> AgentSchema | Response:
    """Create an agent and return it."""
    return await _execute_post_simulation_agents(request, body=body)


@router.get(
    "/simulations/agents",
    response_model=list[AgentSchema],
    status_code=200,
    summary="List simulation agents",
    description="Return simulation agent profiles from DB for View agents and Create form.",
)
@log_route_completion_decorator(route=SIMULATION_AGENTS_ROUTE, success_type=list)
async def get_simulation_agents(
    request: Request,
    limit: int = Query(
        default=DEFAULT_AGENT_LIST_LIMIT,
        ge=1,
        le=MAX_AGENT_LIST_LIMIT,
        description="Maximum number of agents to return (ordered by handle).",
    ),
    offset: int = Query(
        default=DEFAULT_AGENT_LIST_OFFSET,
        ge=0,
        description="Number of agents to skip before returning results (ordered by handle).",
    ),
) -> list[AgentSchema] | Response:
    """Return all simulation agents from the database."""
    return await _execute_get_simulation_agents(request, limit=limit, offset=offset)


@router.get(
    "/simulations/runs",
    response_model=list[RunListItem],
    status_code=200,
    summary="List simulation runs",
    description="Return simulation run summaries for the UI.",
)
@log_route_completion_decorator(route=SIMULATION_RUNS_ROUTE, success_type=list)
async def get_simulation_runs(request: Request) -> list[RunListItem] | Response:
    """Return all simulation runs from the database (app engine backed by SqliteTransactionProvider; DB path from SIM_DB_PATH or local dev DB in LOCAL mode)."""
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
    route=SIMULATION_RUN_ROUTE,
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
    route=SIMULATION_RUN_DETAILS_ROUTE,
    success_type=RunDetailsResponse,
    run_id_from=RunIdSource.RESPONSE,
)
async def get_simulation_run(
    request: Request, run_id: str
) -> RunDetailsResponse | Response:
    """Return run details and turn history for a persisted run."""
    return await _execute_get_simulation_run(request=request, run_id=run_id)


@router.get(
    "/simulations/posts",
    response_model=list[PostSchema],
    status_code=200,
    summary="List simulation posts",
    description="Return posts, optionally filtered by URIs. Batch lookup for feed resolution.",
)
@log_route_completion_decorator(route=SIMULATION_POSTS_ROUTE, success_type=list)
async def get_simulation_posts(
    request: Request,
    uris: list[str] | None = Query(default=None, description="Filter by post URIs"),
) -> list[PostSchema] | Response:
    """Return posts from the database (via SqliteTransactionProvider; DB path from SIM_DB_PATH or local dev DB in LOCAL mode)."""
    return await _execute_get_simulation_posts(request, uris=uris)


@router.get(
    "/simulations/runs/{run_id}/turns",
    response_model=dict[str, TurnSchema],
    status_code=200,
    summary="Get simulation run turns",
    description="Return full per-turn payload for a run ID.",
)
@log_route_completion_decorator(
    route=SIMULATION_RUN_TURNS_ROUTE, success_type=dict, run_id_from=RunIdSource.PATH
)
async def get_simulation_run_turns(
    request: Request, run_id: str
) -> dict[str, TurnSchema] | Response:
    """Return turn payload for a run from the database (via SqliteTransactionProvider; DB path from SIM_DB_PATH or local dev DB in LOCAL mode)."""
    return await _execute_get_simulation_run_turns(request, run_id=run_id)


@timed(attach_attr="duration_ms", log_level=None)
async def _execute_get_metrics(
    request: Request,
) -> list[MetricSchema] | Response:
    """Fetch metrics and convert unexpected failures to HTTP responses."""
    try:
        return await asyncio.to_thread(list_metrics)
    except Exception:
        logger.exception("Unexpected error while listing metrics")
        return _error_response(
            status_code=500,
            code="INTERNAL_ERROR",
            message="Internal server error",
            detail=None,
        )


@timed(attach_attr="duration_ms", log_level=None)
async def _execute_get_feed_algorithms(
    request: Request,
) -> list[FeedAlgorithmSchema] | Response:
    """Fetch feed algorithms and convert unexpected failures to HTTP responses."""
    try:
        return await asyncio.to_thread(list_feed_algorithms)
    except Exception:
        logger.exception("Unexpected error while listing feed algorithms")
        return _error_response(
            status_code=500,
            code="INTERNAL_ERROR",
            message="Internal server error",
            detail=None,
        )


@timed(attach_attr="duration_ms", log_level=None)
async def _execute_get_default_config(
    request: Request,
) -> DefaultConfigSchema | Response:
    """Fetch default config and convert unexpected failures to HTTP responses."""
    try:
        return DEFAULT_SIMULATION_CONFIG
    except Exception:
        logger.exception("Unexpected error while fetching default config")
        return _error_response(
            status_code=500,
            code="INTERNAL_ERROR",
            message="Internal server error",
            detail=None,
        )


@timed(attach_attr="duration_ms", log_level=None)
async def _execute_get_simulation_posts(
    request: Request,
    *,
    uris: list[str] | None = None,
) -> list[PostSchema] | Response:
    """Fetch posts and convert unexpected failures to HTTP responses."""
    try:
        engine = request.app.state.engine
        return await asyncio.to_thread(get_posts_by_uris, uris=uris, engine=engine)
    except Exception:
        logger.exception("Unexpected error while listing simulation posts")
        return _error_response(
            status_code=500,
            code="INTERNAL_ERROR",
            message="Internal server error",
            detail=None,
        )


@timed(attach_attr="duration_ms", log_level=None)
async def _execute_get_simulation_runs(
    request: Request,
) -> list[RunListItem] | Response:
    """Fetch run summaries from the database and convert failures to HTTP responses."""
    try:
        engine = request.app.state.engine
        # Use to_thread for consistency with other async routes and to prepare for real I/O later.
        return await asyncio.to_thread(list_runs, engine=engine)
    except Exception:
        logger.exception("Unexpected error while listing simulation runs")
        return _error_response(
            status_code=500,
            code="INTERNAL_ERROR",
            message="Internal server error",
            detail=None,
        )


@timed(attach_attr="duration_ms", log_level=None)
async def _execute_post_simulation_agents(
    request: Request, *, body: CreateAgentRequest
) -> AgentSchema | Response:
    """Create agent and convert known failures to HTTP responses."""
    try:
        return await asyncio.to_thread(create_agent, body)
    except ApiHandleAlreadyExistsError as e:
        return _error_response(
            status_code=409,
            code="HANDLE_ALREADY_EXISTS",
            message="Agent with this handle already exists",
            detail=e.handle,
        )
    except ValueError as e:
        return _error_response(
            status_code=422,
            code="VALIDATION_ERROR",
            message=str(e),
            detail=None,
        )
    except Exception:
        logger.exception("Unexpected error while creating agent")
        return _error_response(
            status_code=500,
            code="INTERNAL_ERROR",
            message="Internal server error",
            detail=None,
        )


@timed(attach_attr="duration_ms", log_level=None)
async def _execute_get_simulation_agents(
    request: Request,
    *,
    limit: int,
    offset: int,
) -> list[AgentSchema] | Response:
    """Fetch agent list from DB and convert unexpected failures to HTTP responses."""
    try:
        return await asyncio.to_thread(list_agents, limit=limit, offset=offset)
    except Exception:
        logger.exception("Unexpected error while listing simulation agents")
        return _error_response(
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
    engine = request.app.state.engine
    try:
        return await asyncio.to_thread(
            execute,
            request=body,
            engine=engine,
        )
    except ApiRunCreationFailedError as e:
        logger.exception("Simulation run failed before run creation")
        return _error_response(
            status_code=500,
            code="RUN_CREATION_FAILED",
            message=e.message,
            detail=None,
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
async def _execute_get_simulation_run_turns(
    request: Request,
    run_id: str,
) -> dict[str, TurnSchema] | Response:
    """Fetch run turns and convert known failures to HTTP responses."""
    try:
        engine = request.app.state.engine
        return await asyncio.to_thread(get_turns_for_run, run_id=run_id, engine=engine)
    except ApiRunNotFoundError as e:
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
        logger.exception("Unexpected error while fetching run turns")
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
    except ApiRunNotFoundError as e:
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
