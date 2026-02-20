"""Chronological feed generation algorithm.

Sorts posts by creation time, newest first. Limits to MAX_POSTS_PER_FEED.
Uses uri as tie-breaker when created_at is equal for deterministic output.
"""

from feeds.algorithms.interfaces import (
    FeedAlgorithm,
    FeedAlgorithmMetadata,
    FeedAlgorithmResult,
)
from simulation.core.models.agents import SocialMediaAgent
from simulation.core.models.feeds import GeneratedFeed
from simulation.core.models.posts import BlueskyFeedPost

ALGORITHM_ID = "chronological"
METADATA: FeedAlgorithmMetadata = {
    "display_name": "Chronological",
    "description": "Posts sorted by creation time, newest first. Up to 20 posts per feed.",
}
MAX_POSTS_PER_FEED = 20


class ChronologicalFeedAlgorithm(FeedAlgorithm):
    """Feed algorithm that sorts posts by creation time, newest first."""

    @property
    def metadata(self) -> FeedAlgorithmMetadata:
        return METADATA

    def generate(
        self,
        *,
        candidate_posts: list[BlueskyFeedPost],
        agent: SocialMediaAgent,
        limit: int = MAX_POSTS_PER_FEED,
        **kwargs: object,
    ) -> FeedAlgorithmResult:
        """Generate a chronological feed (newest posts first).

        Args:
            candidate_posts: Posts to rank and select from.
            agent: The agent this feed is for.
            limit: Maximum number of posts (default MAX_POSTS_PER_FEED).
            **kwargs: Ignored; for extensibility.

        Returns:
            FeedAlgorithmResult with feed_id, agent_handle, post_uris in order.
        """
        # Sort by created_at desc (newest first); use uri asc as tie-breaker for determinism
        sorted_posts = sorted(candidate_posts, key=lambda p: p.uri)
        sorted_posts = sorted(sorted_posts, key=lambda p: p.created_at, reverse=True)
        selected = sorted_posts[:limit]
        post_uris = [p.uri for p in selected]
        return FeedAlgorithmResult(
            feed_id=GeneratedFeed.generate_feed_id(),
            agent_handle=agent.handle,
            post_uris=post_uris,
        )
