import logging
from collections.abc import Callable

from db.repositories.interfaces import FeedPostRepository, GeneratedFeedRepository
from feeds.algorithms import generate_chronological_feed
from feeds.candidate_generation import load_candidate_posts
from lib.timestamp_utils import get_current_timestamp
from lib.validation_utils import validate_value_in_set
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
_FEED_ALGORITHMS: dict[str, Callable[..., dict[str, str | list[str]]]] = {
    "chronological": generate_chronological_feed,
    # "rag": generate_rag_feed,  # TODO: Add in future PR
}


def generate_feeds(
    agents: list[SocialMediaAgent],
    run_id: str,
    turn_number: int,
    generated_feed_repo: GeneratedFeedRepository,
    feed_post_repo: FeedPostRepository,
    feed_algorithm: str,
) -> dict[str, list[BlueskyFeedPost]]:
    """Generate feeds for all the agents.

    Args:
        agents: List of agents to generate feeds for.
        run_id: The run ID for this simulation.
        turn_number: The turn number for this simulation.
        generated_feed_repo: Repository for writing generated feeds.
        feed_post_repo: Repository for reading feed posts.
        feed_algorithm: Algorithm name to use (must be registered in _FEED_ALGORITHMS).

    Returns:
        Dictionary mapping agent handles to lists of hydrated BlueskyFeedPost objects.

    Raises:
        ValueError: If feed_algorithm is not registered in _FEED_ALGORITHMS.
    """
    feeds = _generate_feeds(
        agents=agents,
        run_id=run_id,
        turn_number=turn_number,
        feed_algorithm=feed_algorithm,
        feed_post_repo=feed_post_repo,
        generated_feed_repo=generated_feed_repo,
    )
    _write_generated_feeds(feeds=feeds, generated_feed_repo=generated_feed_repo)
    return _hydrate_generated_feeds(
        feeds=feeds,
        feed_post_repo=feed_post_repo,
        run_id=run_id,
        turn_number=turn_number,
    )


def _generate_feeds(
    agents: list[SocialMediaAgent],
    run_id: str,
    turn_number: int,
    feed_algorithm: str,
    feed_post_repo: FeedPostRepository,
    generated_feed_repo: GeneratedFeedRepository,
) -> dict[str, GeneratedFeed]:
    """Generate a feed per agent via the feed algorithm; no persistence."""
    feeds: dict[str, GeneratedFeed] = {}
    for agent in agents:
        # TODO: right now we load all posts per agent, but obviously
        # can optimize and personalize later to save on queries.
        feed = _generate_single_agent_feed(
            agent=agent,
            run_id=run_id,
            turn_number=turn_number,
            feed_algorithm=feed_algorithm,
            feed_post_repo=feed_post_repo,
            generated_feed_repo=generated_feed_repo,
        )
        feeds[agent.handle] = feed
    return feeds


def _write_generated_feeds(
    feeds: dict[str, GeneratedFeed],
    generated_feed_repo: GeneratedFeedRepository,
) -> None:
    """Persist each generated feed via the repository."""
    for feed in feeds.values():
        generated_feed_repo.write_generated_feed(feed)


def _load_hydrated_posts(
    feeds: dict[str, GeneratedFeed],
    feed_post_repo: FeedPostRepository,
) -> dict[str, BlueskyFeedPost]:
    """Collect all post URIs from feeds, fetch posts in one batch, return uri -> post map."""
    all_post_uris: set[str] = set()
    for feed in feeds.values():
        all_post_uris.update(feed.post_uris)
    hydrated_posts: list[BlueskyFeedPost] = feed_post_repo.read_feed_posts_by_uris(
        all_post_uris
    )
    return {p.uri: p for p in hydrated_posts}


def _hydrate_generated_feeds(
    feeds: dict[str, GeneratedFeed],
    feed_post_repo: FeedPostRepository,
    run_id: str,
    turn_number: int,
) -> dict[str, list[BlueskyFeedPost]]:
    """Hydrate feeds using a single batch query, then map each feed's URIs to posts."""
    uri_to_post: dict[str, BlueskyFeedPost] = _load_hydrated_posts(
        feeds=feeds, feed_post_repo=feed_post_repo
    )
    agent_to_hydrated_feeds, missing_uris_by_agent = _hydrate_feed_items(
        feeds=feeds, uri_to_post=uri_to_post
    )
    _log_warning_missing_posts(
        missing_uris_by_agent=missing_uris_by_agent,
        feeds=feeds,
        run_id=run_id,
        turn_number=turn_number,
    )
    return agent_to_hydrated_feeds


def _hydrate_feed_items(
    feeds: dict[str, GeneratedFeed],
    uri_to_post: dict[str, BlueskyFeedPost],
) -> tuple[dict[str, list[BlueskyFeedPost]], dict[str, list[str]]]:
    """Map each feed's post URIs to hydrated posts; record missing URIs per agent.

    Missing URIs are skipped in the result and collected for logging. Preserves feed order.
    Returns (agent_to_hydrated_feeds, missing_uris_by_agent).
    """
    missing_uris_by_agent: dict[str, list[str]] = {}
    agent_to_hydrated_feeds: dict[str, list[BlueskyFeedPost]] = {}
    for agent_handle, feed in feeds.items():
        feed_posts: list[BlueskyFeedPost] = []
        for post_uri in feed.post_uris:
            if post_uri not in uri_to_post:
                missing_uris_by_agent.setdefault(agent_handle, []).append(post_uri)
                continue
            feed_posts.append(uri_to_post[post_uri])
        agent_to_hydrated_feeds[agent_handle] = feed_posts
    return (agent_to_hydrated_feeds, missing_uris_by_agent)


def _log_warning_missing_posts(
    missing_uris_by_agent: dict[str, list[str]],
    feeds: dict[str, GeneratedFeed],
    run_id: str,
    turn_number: int,
) -> None:
    """Log one aggregated warning per agent for missing post URIs (first 5 URIs shown, then count)."""
    for agent_handle, missing_uris in missing_uris_by_agent.items():
        feed_id = feeds[agent_handle].feed_id
        missing_count = len(missing_uris)
        uris_preview = missing_uris[:5]
        uris_str = ", ".join(uris_preview)
        if len(missing_uris) > 5:
            uris_str += f", ... ({missing_count - 5} more)"
        logger.warning(
            f"Missing {missing_count} post(s) for agent {agent_handle} in run {run_id}, "
            f"turn {turn_number} (feed_id={feed_id}). Missing URIs: {uris_str}"
        )


def _generate_feed(
    agent: SocialMediaAgent,
    candidate_posts: list[BlueskyFeedPost],
    run_id: str,
    turn_number: int,
    feed_algorithm: str,
) -> GeneratedFeed:
    """Run the registered feed algorithm on candidate posts and return a generated feed."""
    validate_value_in_set(
        feed_algorithm,
        "feed_algorithm",
        _FEED_ALGORITHMS,
        allowed_display_name="registered feed algorithms",
    )
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


def _generate_single_agent_feed(
    agent: SocialMediaAgent,
    run_id: str,
    turn_number: int,
    feed_algorithm: str,
    feed_post_repo: FeedPostRepository,
    generated_feed_repo: GeneratedFeedRepository,
) -> GeneratedFeed:
    """Load candidate posts for one agent, run the feed algorithm, and return the generated feed (no persistence)."""
    candidate_posts: list[BlueskyFeedPost] = load_candidate_posts(
        agent=agent,
        run_id=run_id,
        feed_post_repo=feed_post_repo,
        generated_feed_repo=generated_feed_repo,
    )
    return _generate_feed(
        agent=agent,
        candidate_posts=candidate_posts,
        run_id=run_id,
        turn_number=turn_number,
        feed_algorithm=feed_algorithm,
    )
