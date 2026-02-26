"""Chronological feed generation algorithm.

Sorts posts by creation time, newest first. Limits to caller-supplied limit.
Uses uri as tie-breaker when created_at is equal for deterministic output.
"""

from collections.abc import Mapping

from pydantic import JsonValue

from feeds.algorithms.interfaces import (
    FeedAlgorithm,
    FeedAlgorithmMetadata,
    FeedAlgorithmResult,
)
from simulation.core.models.agents import SocialMediaAgent
from simulation.core.models.feeds import GeneratedFeed
from simulation.core.models.posts import BlueskyFeedPost

ALGORITHM_ID = "chronological"
METADATA: FeedAlgorithmMetadata = FeedAlgorithmMetadata(
    display_name="Chronological",
    description="Posts sorted by creation time, newest first.",
    config_schema={
        "type": "object",
        "properties": {
            "order": {
                "type": "string",
                "title": "Order",
                "description": "Whether to show newest posts first or oldest posts first.",
                "enum": ["newest_first", "oldest_first"],
                "default": "newest_first",
            }
        },
    },
)


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
        limit: int,
        config: Mapping[str, JsonValue] | None = None,
    ) -> FeedAlgorithmResult:
        """Generate a chronological feed (newest posts first).

        Sort by created_at desc (newest first); use uri asc as tie-breaker for determinism.
        Args:
            candidate_posts: Posts to rank and select from.
            agent: The agent this feed is for.
            limit: Maximum number of posts (supplied by caller, e.g. feeds.constants.MAX_POSTS_PER_FEED).

        Returns:
            FeedAlgorithmResult with feed_id, agent_handle, post_uris in order.
        """
        order = config.get("order") if config else None
        reverse = order != "oldest_first"
        sorted_posts = sorted(candidate_posts, key=lambda p: p.uri)
        sorted_posts = sorted(sorted_posts, key=lambda p: p.created_at, reverse=reverse)
        selected = sorted_posts[:limit]
        post_uris = [p.uri for p in selected]
        return FeedAlgorithmResult(
            feed_id=GeneratedFeed.generate_feed_id(),
            agent_handle=agent.handle,
            post_uris=post_uris,
        )
