"""Factory for creating the simulation query service."""

from db.repositories.interfaces import (
    CommentRepository,
    FollowRepository,
    GeneratedFeedRepository,
    LikeRepository,
    MetricsRepository,
    RunFollowEdgeRepository,
    RunPostLikeRepository,
    RunPostRepository,
    RunRepository,
)
from simulation.core.query_service import SimulationQueryService


def create_query_service(
    *,
    run_repo: RunRepository,
    metrics_repo: MetricsRepository,
    run_post_repo: RunPostRepository,
    run_post_like_repo: RunPostLikeRepository,
    generated_feed_repo: GeneratedFeedRepository,
    like_repo: LikeRepository,
    comment_repo: CommentRepository,
    follow_repo: FollowRepository,
    run_follow_edge_repo: RunFollowEdgeRepository,
) -> SimulationQueryService:
    """Create query-side service with read dependencies."""
    return SimulationQueryService(
        run_repo=run_repo,
        metrics_repo=metrics_repo,
        run_post_repo=run_post_repo,
        run_post_like_repo=run_post_like_repo,
        generated_feed_repo=generated_feed_repo,
        like_repo=like_repo,
        comment_repo=comment_repo,
        follow_repo=follow_repo,
        run_follow_edge_repo=run_follow_edge_repo,
    )
