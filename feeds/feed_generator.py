import logging
from typing import Callable

from db.repositories.feed_post_repository import FeedPostRepository
from db.repositories.generated_feed_repository import GeneratedFeedRepository
from feeds.algorithms import generate_chronological_feed
from feeds.candidate_generation import load_candidate_posts
from lib.timestamp_utils import get_current_timestamp
from simulation.core.models.agents import SocialMediaAgent
from simulation.core.models.feeds import GeneratedFeed
from simulation.core.models.posts import BlueskyFeedPost

logger = logging.getLogger(__name__)

# Registry for feed generation algorithms.
# Currently module-level for simplicity. Consider extracting to a separate module
# (e.g., feeds/registry.py) if:
# - We have 4+ algorithms
# - Algorithms need metadata/configuration
# - Algorithms need to be registered from multiple modules
# - Algorithms become complex classes rather than simple functions
_FEED_ALGORITHMS: dict[str, Callable] = {
    "chronological": generate_chronological_feed,
    # "rag": generate_rag_feed,  # TODO: Add in future PR
}


def generate_feed(
    agent: SocialMediaAgent,
    candidate_posts: list[BlueskyFeedPost],
    run_id: str,
    turn_number: int,
    feed_algorithm: str,
) -> GeneratedFeed:
    """Generate a feed for an agent."""
    if feed_algorithm not in _FEED_ALGORITHMS:
        raise ValueError(f"Unknown feed algorithm: {feed_algorithm}")
    algorithm = _FEED_ALGORITHMS[feed_algorithm]
    feed_dict = algorithm(candidate_posts=candidate_posts, agent=agent)
    return GeneratedFeed(
        feed_id=feed_dict["feed_id"],
        run_id=run_id,
        turn_number=turn_number,
        agent_handle=feed_dict["agent_handle"],
        post_uris=feed_dict["post_uris"],
        created_at=get_current_timestamp(),
    )


def generate_feeds(
    agents: list[SocialMediaAgent],
    run_id: str,
    turn_number: int,
    generated_feed_repo: GeneratedFeedRepository,
    feed_post_repo: FeedPostRepository,
    feed_algorithm: str,
) -> dict[str, list[BlueskyFeedPost]]:
    """Generate feeds for all the agents.

    Uses dependency injection for repositories to enable testability and consistency
    with the engine's dependency injection pattern. Uses batch queries for efficient
    post hydration instead of loading all posts.

    Returns a dictionary of agent handles to lists of hydrated BlueskyFeedPost models.

    Does the following:
    1. Generates a feed for each agent using the specified algorithm.
    2. Writes the unhydrated feeds to the database.
    3. Hydrates the posts for each feed using batch queries.
    4. Handles missing posts gracefully (logs warning, skips silently).
    5. Returns a dictionary of agent handles to lists of hydrated BlueskyFeedPost models.

    Args:
        agents: List of agents to generate feeds for.
        run_id: The run ID for this simulation.
        turn_number: The turn number for this simulation.
        generated_feed_repo: Repository for writing generated feeds.
        feed_post_repo: Repository for reading feed posts (used for batch hydration).
        feed_algorithm: Algorithm name to use (must be registered in _FEED_ALGORITHMS).

    Returns:
        Dictionary mapping agent handles to lists of hydrated BlueskyFeedPost objects.

    Raises:
        ValueError: If feed_algorithm is not registered in _FEED_ALGORITHMS.
    """
    feeds: dict[str, GeneratedFeed] = {}
    for agent in agents:
        # TODO (PR 5B): Candidate post loading still creates repositories internally.
        # This is technical debt that should be refactored in a follow-up PR.
        # The load_candidate_posts() function should accept repositories as parameters
        # to maintain consistent dependency injection patterns.
        # Impact: Makes it harder to test generate_feeds() with mocked candidate posts.
        # See: feeds/candidate_generation.py for internal repository creation.
        # TODO: right now we load all posts per agent, but obviously
        # can optimize and personalize later to save on queries.
        candidate_posts: list[BlueskyFeedPost] = load_candidate_posts(
            agent=agent, run_id=run_id
        )
        feed: GeneratedFeed = generate_feed(
            agent=agent,
            candidate_posts=candidate_posts,
            run_id=run_id,
            turn_number=turn_number,
            feed_algorithm=feed_algorithm,
        )
        generated_feed_repo.create_or_update_generated_feed(feed)
        feeds[agent.handle] = feed

    # iterate through feeds, grab only the unique URIs, and hydrate
    all_post_uris: set[str] = set()
    for feed in feeds.values():
        all_post_uris.update(feed.post_uris)

    hydrated_posts: list[BlueskyFeedPost] = feed_post_repo.read_feed_posts_by_uris(
        all_post_uris
    )
    uri_to_post: dict[str, BlueskyFeedPost] = {p.uri: p for p in hydrated_posts}

    # now iterate through feeds and hydrate the posts.
    # Collect missing URIs per agent for aggregated logging
    missing_uris_by_agent: dict[str, list[str]] = {}
    agent_to_hydrated_feeds: dict[str, list[BlueskyFeedPost]] = {}
    for agent_handle, feed in feeds.items():
        feed_posts: list[BlueskyFeedPost] = []
        for post_uri in feed.post_uris:
            # Skip silently if missing. Currently OK and matches other specs
            # related to graceful handling of missing posts. Can be
            # revisited as a fast follow later. Currently, missing posts are an
            # edge case.
            if post_uri not in uri_to_post:
                missing_uris_by_agent.setdefault(agent_handle, []).append(post_uri)
                continue
            feed_posts.append(uri_to_post[post_uri])
        agent_to_hydrated_feeds[agent_handle] = feed_posts

    # Log aggregated warnings for missing posts (one per agent, not per URI)
    for agent_handle, missing_uris in missing_uris_by_agent.items():
        feed_id = feeds[agent_handle].feed_id
        missing_count = len(missing_uris)
        # Show first 5 URIs, then truncate if more
        uris_preview = missing_uris[:5]
        uris_str = ", ".join(uris_preview)
        if len(missing_uris) > 5:
            uris_str += f", ... ({missing_count - 5} more)"
        logger.warning(
            f"Missing {missing_count} post(s) for agent {agent_handle} in run {run_id}, "
            f"turn {turn_number} (feed_id={feed_id}). Missing URIs: {uris_str}"
        )

    return agent_to_hydrated_feeds
