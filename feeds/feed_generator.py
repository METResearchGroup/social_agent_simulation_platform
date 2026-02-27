import logging
from collections.abc import Mapping

from pydantic import JsonValue

from db.repositories.interfaces import FeedPostRepository, GeneratedFeedRepository
from feeds.algorithms import FeedAlgorithmResult, get_feed_generator
from feeds.candidate_generation import load_candidate_posts
from feeds.constants import MAX_POSTS_PER_FEED
from lib.timestamp_utils import get_current_timestamp
from simulation.core.models.agents import SocialMediaAgent
from simulation.core.models.feeds import GeneratedFeed
from simulation.core.models.posts import Post

logger = logging.getLogger(__name__)


def generate_feeds(
    agents: list[SocialMediaAgent],
    run_id: str,
    turn_number: int,
    generated_feed_repo: GeneratedFeedRepository,
    feed_post_repo: FeedPostRepository,
    feed_algorithm: str,
    feed_algorithm_config: Mapping[str, JsonValue] | None = None,
) -> dict[str, list[Post]]:
    """Generate feeds for all the agents.

    Args:
        agents: List of agents to generate feeds for.
        run_id: The run ID for this simulation.
        turn_number: The turn number for this simulation.
        generated_feed_repo: Repository for writing generated feeds.
        feed_post_repo: Repository for reading feed posts.
        feed_algorithm: Algorithm name to use (must be registered in feeds.algorithms).

    Returns:
        Dictionary mapping agent handles to lists of hydrated Post objects.

    Raises:
        ValueError: If feed_algorithm is not registered in feeds.algorithms.
    """
    feeds = _generate_feeds(
        agents=agents,
        run_id=run_id,
        turn_number=turn_number,
        generated_feed_repo=generated_feed_repo,
        feed_post_repo=feed_post_repo,
        feed_algorithm=feed_algorithm,
        feed_algorithm_config=feed_algorithm_config,
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
    generated_feed_repo: GeneratedFeedRepository,
    feed_post_repo: FeedPostRepository,
    feed_algorithm: str,
    feed_algorithm_config: Mapping[str, JsonValue] | None,
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
            generated_feed_repo=generated_feed_repo,
            feed_post_repo=feed_post_repo,
            feed_algorithm=feed_algorithm,
            feed_algorithm_config=feed_algorithm_config,
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
) -> dict[str, Post]:
    """Collect all post IDs from feeds, fetch posts in one batch, return post_id -> post map."""
    all_post_ids: set[str] = set()
    for feed in feeds.values():
        all_post_ids.update(feed.post_ids)
    hydrated_posts: list[Post] = feed_post_repo.read_feed_posts_by_ids(all_post_ids)
    return {p.post_id: p for p in hydrated_posts}


def _hydrate_generated_feeds(
    feeds: dict[str, GeneratedFeed],
    feed_post_repo: FeedPostRepository,
    run_id: str,
    turn_number: int,
) -> dict[str, list[Post]]:
    """Hydrate feeds using a single batch query, then map each feed's post IDs to posts."""
    post_id_to_post: dict[str, Post] = _load_hydrated_posts(
        feeds=feeds, feed_post_repo=feed_post_repo
    )
    agent_to_hydrated_feeds, missing_post_ids_by_agent = _hydrate_feed_items(
        feeds=feeds, post_id_to_post=post_id_to_post
    )
    _log_warning_missing_posts(
        missing_post_ids_by_agent=missing_post_ids_by_agent,
        feeds=feeds,
        run_id=run_id,
        turn_number=turn_number,
    )
    return agent_to_hydrated_feeds


def _hydrate_feed_items(
    feeds: dict[str, GeneratedFeed],
    post_id_to_post: dict[str, Post],
) -> tuple[dict[str, list[Post]], dict[str, list[str]]]:
    """Map each feed's post IDs to hydrated posts; record missing IDs per agent.

    Missing IDs are skipped in the result and collected for logging. Preserves feed order.
    Returns (agent_to_hydrated_feeds, missing_post_ids_by_agent).
    """
    missing_post_ids_by_agent: dict[str, list[str]] = {}
    agent_to_hydrated_feeds: dict[str, list[Post]] = {}
    for agent_handle, feed in feeds.items():
        feed_posts: list[Post] = []
        for post_id in feed.post_ids:
            if post_id not in post_id_to_post:
                missing_post_ids_by_agent.setdefault(agent_handle, []).append(post_id)
                continue
            feed_posts.append(post_id_to_post[post_id])
        agent_to_hydrated_feeds[agent_handle] = feed_posts
    return (agent_to_hydrated_feeds, missing_post_ids_by_agent)


def _log_warning_missing_posts(
    missing_post_ids_by_agent: dict[str, list[str]],
    feeds: dict[str, GeneratedFeed],
    run_id: str,
    turn_number: int,
) -> None:
    """Log one aggregated warning per agent for missing post IDs (first 5 IDs shown, then count)."""
    for agent_handle, missing_post_ids in missing_post_ids_by_agent.items():
        feed_id = feeds[agent_handle].feed_id
        missing_count = len(missing_post_ids)
        ids_preview = missing_post_ids[:5]
        ids_str = ", ".join(ids_preview)
        if len(missing_post_ids) > 5:
            ids_str += f", ... ({missing_count - 5} more)"
        logger.warning(
            f"Missing {missing_count} post(s) for agent {agent_handle} in run {run_id}, "
            f"turn {turn_number} (feed_id={feed_id}). Missing post_ids: {ids_str}"
        )


def _generate_feed(
    agent: SocialMediaAgent,
    candidate_posts: list[Post],
    run_id: str,
    turn_number: int,
    feed_algorithm: str,
    feed_algorithm_config: Mapping[str, JsonValue] | None,
) -> GeneratedFeed:
    """Run the registered feed algorithm on candidate posts and return a generated feed."""
    algorithm = get_feed_generator(feed_algorithm)
    result: FeedAlgorithmResult = algorithm.generate(
        candidate_posts=candidate_posts,
        agent=agent,
        limit=MAX_POSTS_PER_FEED,
        config=feed_algorithm_config,
    )
    return GeneratedFeed(
        feed_id=result.feed_id,
        run_id=run_id,
        turn_number=turn_number,
        agent_handle=result.agent_handle,
        post_ids=result.post_ids,
        created_at=get_current_timestamp(),
    )


def _generate_single_agent_feed(
    agent: SocialMediaAgent,
    run_id: str,
    turn_number: int,
    generated_feed_repo: GeneratedFeedRepository,
    feed_post_repo: FeedPostRepository,
    feed_algorithm: str,
    feed_algorithm_config: Mapping[str, JsonValue] | None,
) -> GeneratedFeed:
    """Load candidate posts for one agent, run the feed algorithm, and return the generated feed (no persistence)."""
    candidate_posts: list[Post] = load_candidate_posts(
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
        feed_algorithm_config=feed_algorithm_config,
    )
