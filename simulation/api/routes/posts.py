"""Simulation posts API routes."""

import asyncio
from typing import Annotated

from fastapi import APIRouter, Query, Request
from fastapi.responses import Response

from lib.decorators import timed
from lib.request_logging import log_route_completion_decorator
from simulation.api.schemas.simulation import PostSchema
from simulation.api.services.run_query_service import get_posts_by_ids

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
    post_ids: Annotated[
        list[str] | None, Query(description="Filter by canonical post_ids")
    ] = None,
) -> list[PostSchema] | Response:
    """Return posts from the database (via SqliteTransactionProvider; DB path from SIM_DB_PATH or local dev DB in LOCAL mode)."""
    return await _execute_get_simulation_posts(request, post_ids=post_ids)


@timed(attach_attr="duration_ms", log_level=None)
async def _execute_get_simulation_posts(
    request: Request,
    *,
    post_ids: list[str] | None = None,
) -> list[PostSchema] | Response:
    """Fetch posts."""
    engine = request.app.state.deps.engine
    return await asyncio.to_thread(get_posts_by_ids, post_ids=post_ids, engine=engine)
