"""Chronological feed generation algorithm.

Sorts posts by creation time, newest first. Limits to MAX_POSTS_PER_FEED.
"""

from feeds.algorithms.interfaces import FeedAlgorithmMetadata
from simulation.core.models.agents import SocialMediaAgent
from simulation.core.models.feeds import GeneratedFeed
from simulation.core.models.posts import BlueskyFeedPost

ALGORITHM_ID = "chronological"
METADATA: FeedAlgorithmMetadata = {
    "display_name": "Chronological",
    "description": "Posts sorted by creation time, newest first. Up to 20 posts per feed.",
}
MAX_POSTS_PER_FEED = 20


def generate(
    *,
    candidate_posts: list[BlueskyFeedPost],
    agent: SocialMediaAgent,
    limit: int = MAX_POSTS_PER_FEED,
    **kwargs: object,
) -> dict:
    """Generate a chronological feed (newest posts first).

    Args:
        candidate_posts: Posts to rank and select from.
        agent: The agent this feed is for.
        limit: Maximum number of posts (default MAX_POSTS_PER_FEED).
        **kwargs: Ignored; for extensibility.

    Returns:
        Dict with feed_id, agent_handle, post_uris.
    """
    sorted_posts = sorted(
        candidate_posts,
        key=lambda p: p.created_at,
        reverse=True,
    )
    selected = sorted_posts[:limit]
    post_uris = [p.uri for p in selected]
    return {
        "feed_id": GeneratedFeed.generate_feed_id(),
        "agent_handle": agent.handle,
        "post_uris": post_uris,
    }
