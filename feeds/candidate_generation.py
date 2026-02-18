"""Generate candidate posts for the feeds."""

from db.repositories.interfaces import FeedPostRepository, GeneratedFeedRepository
from simulation.core.models.agents import SocialMediaAgent
from simulation.core.models.posts import BlueskyFeedPost


def load_candidate_posts(
    *,
    agent: SocialMediaAgent,
    run_id: str,
    feed_post_repo: FeedPostRepository,
    generated_feed_repo: GeneratedFeedRepository,
) -> list[BlueskyFeedPost]:
    """Load candidate posts for an agent's feed, excluding already-seen and self-authored posts.

    Args:
        agent: The agent to load candidates for.
        run_id: The current simulation run ID.
        feed_post_repo: Repository for reading feed posts.
        generated_feed_repo: Repository for reading previously generated feeds.

    Returns:
        Filtered list of candidate posts.
    """
    candidate_posts: list[BlueskyFeedPost] = feed_post_repo.list_all_feed_posts()
    return _filter_candidate_posts(
        candidate_posts=candidate_posts,
        agent=agent,
        run_id=run_id,
        generated_feed_repo=generated_feed_repo,
    )


def _filter_candidate_posts(
    *,
    candidate_posts: list[BlueskyFeedPost],
    agent: SocialMediaAgent,
    run_id: str,
    generated_feed_repo: GeneratedFeedRepository,
) -> list[BlueskyFeedPost]:
    """Filter out posts the agent has already seen or authored."""
    seen_post_uris: set[str] = generated_feed_repo.get_post_uris_for_run(
        agent_handle=agent.handle, run_id=run_id
    )
    return [
        p
        for p in candidate_posts
        if p.uri not in seen_post_uris and p.author_handle != agent.handle
    ]
