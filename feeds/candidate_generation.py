"""Generate candidate posts for the feeds."""

from db.repositories.interfaces import FeedPostRepository, GeneratedFeedRepository
from simulation.core.models.agents import SocialMediaAgent
from simulation.core.models.posts import Post


# TODO: we can get arbitrarily complex with how we do this later
# on, but as a first pass it's easy enough to just load all the posts.
def load_posts(*, feed_post_repo: FeedPostRepository) -> list[Post]:
    """Load the posts for the feeds."""
    return feed_post_repo.list_all_feed_posts()


def load_seen_post_ids(
    *,
    agent: SocialMediaAgent,
    run_id: str,
    generated_feed_repo: GeneratedFeedRepository,
) -> set[str]:
    """Load the posts that the agent has already seen in the given run.

    Returns a set of post_ids.
    """
    return generated_feed_repo.get_post_ids_for_run(
        agent_handle=agent.handle, run_id=run_id
    )


def filter_candidate_posts(
    *,
    candidate_posts: list[Post],
    agent: SocialMediaAgent,
    run_id: str,
    generated_feed_repo: GeneratedFeedRepository,
) -> list[Post]:
    """Filter the posts that are candidates for the feeds.

    Remove posts that:
    - The agent has already seen.
    - The agent themselves posted (or their original Bluesky profile posted)
    """

    seen_post_ids: set[str] = load_seen_post_ids(
        agent=agent, run_id=run_id, generated_feed_repo=generated_feed_repo
    )
    candidate_posts = [
        p
        for p in candidate_posts
        if p.post_id not in seen_post_ids and p.author_handle != agent.handle
    ]

    return candidate_posts


def load_candidate_posts(
    *,
    agent: SocialMediaAgent,
    run_id: str,
    feed_post_repo: FeedPostRepository,
    generated_feed_repo: GeneratedFeedRepository,
) -> list[Post]:
    """Load the candidate posts for the feeds.

    Remove posts that:
    - The agent has already seen.
    - The agent themselves posted (or their original Bluesky profile posted)
    """
    candidate_posts: list[Post] = load_posts(feed_post_repo=feed_post_repo)
    candidate_posts = filter_candidate_posts(
        candidate_posts=candidate_posts,
        agent=agent,
        run_id=run_id,
        generated_feed_repo=generated_feed_repo,
    )
    return candidate_posts
