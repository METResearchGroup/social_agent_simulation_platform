"""Metadata API routes (feed algorithms, metrics, default config)."""

import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import Response

from lib.decorators import timed
from lib.request_logging import log_route_completion_decorator
from simulation.api.constants import DEFAULT_SIMULATION_CONFIG
from simulation.api.schemas.simulation import (
    DefaultConfigSchema,
    FeedAlgorithmSchema,
    MetricSchema,
)
from simulation.api.services.metadata_service import list_feed_algorithms, list_metrics

router = APIRouter()

FEED_ALGORITHMS_ROUTE: str = "GET /v1/simulations/feed-algorithms"
METRICS_ROUTE: str = "GET /v1/simulations/metrics"
CONFIG_DEFAULT_ROUTE: str = "GET /v1/simulations/config/default"


@router.get(
    "/simulations/feed-algorithms",
    response_model=list[FeedAlgorithmSchema],
    status_code=200,
    summary="List feed algorithms",
    description="Return available feed algorithms with metadata for the UI.",
)
@log_route_completion_decorator(route=FEED_ALGORITHMS_ROUTE, success_type=list)
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
@log_route_completion_decorator(route=METRICS_ROUTE, success_type=list)
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
    route=CONFIG_DEFAULT_ROUTE, success_type=DefaultConfigSchema
)
async def get_simulation_config_default(
    request: Request,
) -> DefaultConfigSchema | Response:
    """Return default config for simulation start form."""
    return await _execute_get_default_config(request)


@timed(attach_attr="duration_ms", log_level=None)
async def _execute_get_metrics(
    request: Request,
) -> list[MetricSchema] | Response:
    """Fetch metrics."""
    return await asyncio.to_thread(list_metrics)


@timed(attach_attr="duration_ms", log_level=None)
async def _execute_get_feed_algorithms(
    request: Request,
) -> list[FeedAlgorithmSchema] | Response:
    """Fetch feed algorithms."""
    return await asyncio.to_thread(list_feed_algorithms)


@timed(attach_attr="duration_ms", log_level=None)
async def _execute_get_default_config(
    request: Request,
) -> DefaultConfigSchema | Response:
    """Fetch default config."""
    return DEFAULT_SIMULATION_CONFIG
