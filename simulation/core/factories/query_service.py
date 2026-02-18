"""Factory for creating the simulation query service."""

from db.repositories.interfaces import (
    FeedPostRepository,
    GeneratedFeedRepository,
    MetricsRepository,
    RunRepository,
)
from simulation.core.query_service import SimulationQueryService


def create_query_service(
    *,
    run_repo: RunRepository,
    metrics_repo: MetricsRepository,
    feed_post_repo: FeedPostRepository,
    generated_feed_repo: GeneratedFeedRepository,
) -> SimulationQueryService:
    """Create query-side service with read dependencies."""
    return SimulationQueryService(
        run_repo=run_repo,
        metrics_repo=metrics_repo,
        feed_post_repo=feed_post_repo,
        generated_feed_repo=generated_feed_repo,
    )
