"""Generate candidate posts for the feeds."""

from db.adapters.sqlite.sqlite import SqliteTransactionProvider
from db.repositories.feed_post_repository import create_sqlite_feed_post_repository
from db.repositories.generated_feed_repository import (
    create_sqlite_generated_feed_repository,
)
from simulation.core.models.agents import SocialMediaAgent
from simulation.core.models.posts import BlueskyFeedPost


# TODO: we can get arbitrarily complex with how we do this later
# on, but as a first pass it's easy enough to just load all the posts.
def load_posts() -> list[BlueskyFeedPost]:
    """Load the posts for the feeds."""
    tx = SqliteTransactionProvider()
    feed_post_repo = create_sqlite_feed_post_repository(transaction_provider=tx)
    return feed_post_repo.list_all_feed_posts()


def load_seen_post_uris(agent: SocialMediaAgent, run_id: str) -> set[str]:
    """Load the posts that the agent has already seen in the given run.

    Returns a set of URIs.
    """
    tx = SqliteTransactionProvider()
    generated_feed_repo = create_sqlite_generated_feed_repository(
        transaction_provider=tx
    )
    return generated_feed_repo.get_post_uris_for_run(
        agent_handle=agent.handle, run_id=run_id
    )


def filter_candidate_posts(
    candidate_posts: list[BlueskyFeedPost], agent: SocialMediaAgent, run_id: str
) -> list[BlueskyFeedPost]:
    """Filter the posts that are candidates for the feeds.

    Remove posts that:
    - The agent has already seen.
    - The agent themselves posted (or their original Bluesky profile posted)
    """

    seen_post_uris: set[str] = load_seen_post_uris(agent=agent, run_id=run_id)
    candidate_posts = [
        p
        for p in candidate_posts
        if p.uri not in seen_post_uris and p.author_handle != agent.handle
    ]

    return candidate_posts


def load_candidate_posts(agent: SocialMediaAgent, run_id: str) -> list[BlueskyFeedPost]:
    """Load the candidate posts for the feeds.

    Remove posts that:
    - The agent has already seen.
    - The agent themselves posted (or their original Bluesky profile posted)
    """
    candidate_posts: list[BlueskyFeedPost] = load_posts()
    candidate_posts = filter_candidate_posts(
        candidate_posts=candidate_posts, agent=agent, run_id=run_id
    )
    return candidate_posts
