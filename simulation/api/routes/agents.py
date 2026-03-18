"""Simulation agent API routes."""

import asyncio
import logging

from fastapi import APIRouter, Query, Request
from fastapi.responses import Response

from lib.decorators import timed
from lib.rate_limiting import RATE_LIMIT_AGENTS_CREATE, limiter
from lib.request_logging import log_route_completion_decorator
from simulation.api.constants import (
    DEFAULT_AGENT_LIST_LIMIT,
    DEFAULT_AGENT_LIST_OFFSET,
    MAX_AGENT_LIST_LIMIT,
)
from simulation.api.errors import (
    ApiAgentFollowEdgeAlreadyExistsError,
    ApiAgentFollowEdgeNotFoundError,
    ApiAgentNotFoundError,
    ApiHandleAlreadyExistsError,
    ApiSelfFollowNotAllowedError,
    ApiTargetAgentNotFoundError,
)
from simulation.api.routes._helpers import error_response
from simulation.api.schemas.simulation import (
    AgentFollowEdgeSchema,
    AgentSchema,
    CreateAgentFollowRequest,
    CreateAgentRequest,
    ListAgentFollowsResponse,
)
from simulation.api.services.agent_command_service import create_agent, delete_agent
from simulation.api.services.agent_follows_command_service import (
    create_agent_follow,
    delete_agent_follow,
)
from simulation.api.services.agent_follows_query_service import list_agent_follows
from simulation.api.services.agent_query_service import list_agents

logger = logging.getLogger(__name__)

router = APIRouter()

AGENTS_ROUTE: str = "GET /v1/simulations/agents"
AGENTS_CREATE_ROUTE: str = "POST /v1/simulations/agents"
AGENTS_DELETE_ROUTE: str = "DELETE /v1/simulations/agents/{handle}"
AGENT_FOLLOWS_ROUTE: str = "GET /v1/simulations/agents/{handle}/follows"
AGENT_FOLLOWS_CREATE_ROUTE: str = "POST /v1/simulations/agents/{handle}/follows"
AGENT_FOLLOWS_DELETE_ROUTE: str = (
    "DELETE /v1/simulations/agents/{handle}/follows/{target_handle}"
)


@router.post(
    "/simulations/agents",
    response_model=AgentSchema,
    status_code=201,
    summary="Create simulation agent",
    description="Create a user-generated agent.",
)
@limiter.limit(RATE_LIMIT_AGENTS_CREATE)
@log_route_completion_decorator(route=AGENTS_CREATE_ROUTE, success_type=AgentSchema)
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
@log_route_completion_decorator(route=AGENTS_ROUTE, success_type=list)
async def get_simulation_agents(
    request: Request,
    q: str | None = Query(
        default=None,
        max_length=200,
        description=(
            "Optional handle search query (case-insensitive substring). "
            "Supports '*' (any-length) and '?' (single-character) wildcards."
        ),
    ),
    limit: int = Query(
        default=DEFAULT_AGENT_LIST_LIMIT,
        ge=1,
        le=MAX_AGENT_LIST_LIMIT,
        description=(
            "Maximum number of agents to return (ordered by updated_at DESC, handle ASC)."
        ),
    ),
    offset: int = Query(
        default=DEFAULT_AGENT_LIST_OFFSET,
        ge=0,
        description=(
            "Number of agents to skip before returning results (ordered by updated_at DESC, handle ASC)."
        ),
    ),
) -> list[AgentSchema] | Response:
    """Return all simulation agents from the database."""
    return await _execute_get_simulation_agents(
        request, q=q, limit=limit, offset=offset
    )


@router.get(
    "/simulations/agents/{handle}/follows",
    response_model=ListAgentFollowsResponse,
    status_code=200,
    summary="List seed-state follows for an agent",
    description="Return editable pre-run follow edges for the given agent handle.",
)
@log_route_completion_decorator(
    route=AGENT_FOLLOWS_ROUTE,
    success_type=ListAgentFollowsResponse,
)
async def get_simulation_agent_follows(
    request: Request,
    handle: str,
    limit: int = Query(
        default=DEFAULT_AGENT_LIST_LIMIT,
        ge=1,
        le=MAX_AGENT_LIST_LIMIT,
        description="Maximum number of follow edges to return.",
    ),
    offset: int = Query(
        default=DEFAULT_AGENT_LIST_OFFSET,
        ge=0,
        description="Number of follow edges to skip before returning results.",
    ),
) -> ListAgentFollowsResponse | Response:
    """Return paginated editable follow edges for the given agent handle."""
    return await _execute_get_simulation_agent_follows(
        request,
        handle=handle,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/simulations/agents/{handle}/follows",
    response_model=AgentFollowEdgeSchema,
    status_code=201,
    summary="Create seed-state follow edge",
    description="Create an editable pre-run follow edge between two internal agents.",
)
@log_route_completion_decorator(
    route=AGENT_FOLLOWS_CREATE_ROUTE,
    success_type=AgentFollowEdgeSchema,
)
async def post_simulation_agent_follows(
    request: Request,
    handle: str,
    body: CreateAgentFollowRequest,
) -> AgentFollowEdgeSchema | Response:
    """Create one editable follow edge for the given agent handle."""
    return await _execute_post_simulation_agent_follows(
        request,
        handle=handle,
        body=body,
    )


@router.delete(
    "/simulations/agents/{handle}/follows/{target_handle}",
    status_code=204,
    summary="Delete seed-state follow edge",
    description="Delete an editable pre-run follow edge between two internal agents.",
)
@log_route_completion_decorator(
    route=AGENT_FOLLOWS_DELETE_ROUTE,
    success_type=type(None),
)
async def delete_simulation_agent_follow(
    request: Request,
    handle: str,
    target_handle: str,
) -> Response:
    """Delete one editable follow edge for the given agent handle."""
    return await _execute_delete_simulation_agent_follow(
        request,
        handle=handle,
        target_handle=target_handle,
    )


@router.delete(
    "/simulations/agents/{handle}",
    status_code=204,
    summary="Delete simulation agent",
    description="Delete a simulation agent by handle.",
)
@log_route_completion_decorator(route=AGENTS_DELETE_ROUTE, success_type=type(None))
async def delete_simulation_agent(request: Request, handle: str) -> Response:
    """Delete an agent and its related data."""
    return await _execute_delete_simulation_agent(request, handle=handle)


@timed(attach_attr="duration_ms", log_level=None)
async def _execute_post_simulation_agents(
    request: Request, *, body: CreateAgentRequest
) -> AgentSchema | Response:
    """Create agent and convert known failures to HTTP responses."""
    try:
        ctx = request.app.state.context
        return await asyncio.to_thread(
            create_agent,
            body,
            transaction_provider=ctx.transaction_provider,
            agent_repo=ctx.agent_repo,
            bio_repo=ctx.agent_bio_repo,
            metadata_repo=ctx.agent_metadata_repo,
        )
    except ApiHandleAlreadyExistsError as e:
        return error_response(
            status_code=409,
            code="HANDLE_ALREADY_EXISTS",
            message="Agent with this handle already exists",
            detail=e.handle,
        )
    except ValueError as e:
        return error_response(
            status_code=422,
            code="VALIDATION_ERROR",
            message=str(e),
            detail=None,
        )
    except Exception:
        logger.exception("Unexpected error while creating agent")
        return error_response(
            status_code=500,
            code="INTERNAL_ERROR",
            message="Internal server error",
            detail=None,
        )


@timed(attach_attr="duration_ms", log_level=None)
async def _execute_get_simulation_agents(
    request: Request,
    *,
    q: str | None,
    limit: int,
    offset: int,
) -> list[AgentSchema] | Response:
    """Fetch agent list from DB and convert unexpected failures to HTTP responses."""
    try:
        ctx = request.app.state.context
        return await asyncio.to_thread(
            list_agents,
            agent_repo=ctx.agent_repo,
            bio_repo=ctx.agent_bio_repo,
            metadata_repo=ctx.agent_metadata_repo,
            q=q,
            limit=limit,
            offset=offset,
        )
    except Exception:
        logger.exception("Unexpected error while listing simulation agents")
        return error_response(
            status_code=500,
            code="INTERNAL_ERROR",
            message="Internal server error",
            detail=None,
        )


@timed(attach_attr="duration_ms", log_level=None)
async def _execute_get_simulation_agent_follows(
    request: Request,
    *,
    handle: str,
    limit: int,
    offset: int,
) -> ListAgentFollowsResponse | Response:
    """Fetch seed-state follow edges and convert known failures to HTTP responses."""
    try:
        ctx = request.app.state.context
        return await asyncio.to_thread(
            list_agent_follows,
            handle,
            agent_repo=ctx.agent_repo,
            agent_follow_edge_repo=ctx.agent_follow_edge_repo,
            limit=limit,
            offset=offset,
        )
    except ApiAgentNotFoundError as e:
        return error_response(
            status_code=404,
            code="AGENT_NOT_FOUND",
            message="Agent not found",
            detail=e.handle,
        )
    except ValueError as e:
        return error_response(
            status_code=422,
            code="VALIDATION_ERROR",
            message=str(e),
            detail=None,
        )
    except Exception:
        logger.exception("Unexpected error while listing simulation agent follows")
        return error_response(
            status_code=500,
            code="INTERNAL_ERROR",
            message="Internal server error",
            detail=None,
        )


@timed(attach_attr="duration_ms", log_level=None)
async def _execute_post_simulation_agent_follows(
    request: Request,
    *,
    handle: str,
    body: CreateAgentFollowRequest,
) -> AgentFollowEdgeSchema | Response:
    """Create seed-state follow edge and convert known failures to HTTP responses."""
    try:
        ctx = request.app.state.context
        return await asyncio.to_thread(
            create_agent_follow,
            handle,
            body,
            transaction_provider=ctx.transaction_provider,
            agent_repo=ctx.agent_repo,
            agent_follow_edge_repo=ctx.agent_follow_edge_repo,
            metadata_repo=ctx.agent_metadata_repo,
        )
    except ApiAgentNotFoundError as e:
        return error_response(
            status_code=404,
            code="AGENT_NOT_FOUND",
            message="Agent not found",
            detail=e.handle,
        )
    except ApiTargetAgentNotFoundError as e:
        return error_response(
            status_code=404,
            code="TARGET_AGENT_NOT_FOUND",
            message="Target agent not found",
            detail=e.handle,
        )
    except ApiAgentFollowEdgeAlreadyExistsError as e:
        return error_response(
            status_code=409,
            code="FOLLOW_EDGE_ALREADY_EXISTS",
            message="Follow edge already exists",
            detail=f"{e.follower_handle}->{e.target_handle}",
        )
    except ApiSelfFollowNotAllowedError as e:
        return error_response(
            status_code=422,
            code="SELF_FOLLOW_NOT_ALLOWED",
            message="Agent cannot follow itself",
            detail=e.handle,
        )
    except ValueError as e:
        return error_response(
            status_code=422,
            code="VALIDATION_ERROR",
            message=str(e),
            detail=None,
        )
    except Exception:
        logger.exception("Unexpected error while creating simulation agent follow edge")
        return error_response(
            status_code=500,
            code="INTERNAL_ERROR",
            message="Internal server error",
            detail=None,
        )


@timed(attach_attr="duration_ms", log_level=None)
async def _execute_delete_simulation_agent_follow(
    request: Request,
    *,
    handle: str,
    target_handle: str,
) -> Response:
    """Delete seed-state follow edge and convert known failures to HTTP responses."""
    try:
        ctx = request.app.state.context
        await asyncio.to_thread(
            delete_agent_follow,
            handle,
            target_handle,
            transaction_provider=ctx.transaction_provider,
            agent_repo=ctx.agent_repo,
            agent_follow_edge_repo=ctx.agent_follow_edge_repo,
            metadata_repo=ctx.agent_metadata_repo,
        )
        return Response(status_code=204)
    except ApiAgentNotFoundError as e:
        return error_response(
            status_code=404,
            code="AGENT_NOT_FOUND",
            message="Agent not found",
            detail=e.handle,
        )
    except ApiTargetAgentNotFoundError as e:
        return error_response(
            status_code=404,
            code="TARGET_AGENT_NOT_FOUND",
            message="Target agent not found",
            detail=e.handle,
        )
    except ApiAgentFollowEdgeNotFoundError as e:
        return error_response(
            status_code=404,
            code="FOLLOW_EDGE_NOT_FOUND",
            message="Follow edge not found",
            detail=f"{e.follower_handle}->{e.target_handle}",
        )
    except ValueError as e:
        return error_response(
            status_code=422,
            code="VALIDATION_ERROR",
            message=str(e),
            detail=None,
        )
    except Exception:
        logger.exception("Unexpected error while deleting simulation agent follow edge")
        return error_response(
            status_code=500,
            code="INTERNAL_ERROR",
            message="Internal server error",
            detail=None,
        )


@timed(attach_attr="duration_ms", log_level=None)
async def _execute_delete_simulation_agent(
    request: Request, *, handle: str
) -> Response:
    """Delete agent and convert known failures to HTTP responses."""
    try:
        ctx = request.app.state.context
        await asyncio.to_thread(
            delete_agent,
            handle,
            transaction_provider=ctx.transaction_provider,
            agent_repo=ctx.agent_repo,
            bio_repo=ctx.agent_bio_repo,
            agent_follow_edge_repo=ctx.agent_follow_edge_repo,
            metadata_repo=ctx.agent_metadata_repo,
        )
        return Response(status_code=204)
    except ApiAgentNotFoundError as e:
        return error_response(
            status_code=404,
            code="AGENT_NOT_FOUND",
            message="Agent not found",
            detail=e.handle,
        )
    except ValueError as e:
        return error_response(
            status_code=422,
            code="VALIDATION_ERROR",
            message=str(e),
            detail=None,
        )
    except Exception:
        logger.exception("Unexpected error while deleting agent")
        return error_response(
            status_code=500,
            code="INTERNAL_ERROR",
            message="Internal server error",
            detail=None,
        )
