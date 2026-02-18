"""Container logic for different feed generation algorithms"""

# TODO: for now, we'll generate the feeds in real-time during the simulations,
# but in practice we would generate them offline.
from simulation.core.models.agents import SocialMediaAgent
from simulation.core.models.feeds import GeneratedFeed
from simulation.core.models.posts import BlueskyFeedPost

MAX_POSTS_PER_FEED: int = 20


def generate_chronological_feed(
    candidate_posts: list[BlueskyFeedPost],
    agent: SocialMediaAgent,
    limit: int = MAX_POSTS_PER_FEED,
) -> dict[str, str | list[str]]:
    """Generate a chronological feed for an agent."""
    # TODO: fast follow: insert randomness so that the feed isn't always the
    # same across rounds.
    sorted_posts = sorted(candidate_posts, key=lambda p: p.created_at, reverse=True)
    sorted_posts = sorted_posts[:limit]
    feed_id = GeneratedFeed.generate_feed_id()
    return {
        "feed_id": feed_id,
        "agent_handle": agent.handle,
        "post_uris": [p.uri for p in sorted_posts],
    }


# TODO: placeholder for next ticket.
def generate_rag_feed() -> GeneratedFeed:
    raise NotImplementedError("RAG feed generation not yet implemented")
