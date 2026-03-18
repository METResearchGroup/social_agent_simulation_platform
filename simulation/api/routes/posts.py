"""Simulation posts API routes."""

import asyncio
import logging

from fastapi import APIRouter, Query, Request
from fastapi.responses import Response

from lib.decorators import timed
from lib.request_logging import log_route_completion_decorator
from simulation.api.routes._helpers import error_response
from simulation.api.schemas.simulation import PostSchema
from simulation.api.services.run_query_service import get_posts_by_ids

logger = logging.getLogger(__name__)

router = APIRouter()

POSTS_ROUTE: str = "GET /v1/simulations/posts"


@router.get(
    "/simulations/posts",
    response_model=list[PostSchema],
    status_code=200,
    summary="List simulation posts",
    description="Return posts, optionally filtered by canonical post_ids. Batch lookup for feed resolution.",
)
@log_route_completion_decorator(route=POSTS_ROUTE, success_type=list)
async def get_simulation_posts(
    request: Request,
    post_ids: list[str] | None = Query(
        default=None, description="Filter by canonical post_ids"
    ),
) -> list[PostSchema] | Response:
    """Return posts from the database (via SqliteTransactionProvider; DB path from SIM_DB_PATH or local dev DB in LOCAL mode)."""
    return await _execute_get_simulation_posts(request, post_ids=post_ids)


@timed(attach_attr="duration_ms", log_level=None)
async def _execute_get_simulation_posts(
    request: Request,
    *,
    post_ids: list[str] | None = None,
) -> list[PostSchema] | Response:
    """Fetch posts and convert unexpected failures to HTTP responses."""
    try:
        engine = request.app.state.engine
        return await asyncio.to_thread(
            get_posts_by_ids, post_ids=post_ids, engine=engine
        )
    except Exception:
        logger.exception("Unexpected error while listing simulation posts")
        return error_response(
            status_code=500,
            code="INTERNAL_ERROR",
            message="Internal server error",
            detail=None,
        )
