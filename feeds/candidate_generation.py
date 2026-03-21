"""Generate candidate posts for the feeds."""

from db.repositories.interfaces import (
    GeneratedFeedRepository,
    RunPostCommentRepository,
    RunPostLikeRepository,
    RunPostRepository,
)
from simulation.core.models.agents import SimulationAgent
from simulation.core.models.posts import Post, run_post_snapshot_to_post


def load_posts(
    *,
    run_id: str,
    run_post_repo: RunPostRepository,
    run_post_like_repo: RunPostLikeRepository,
    run_post_comment_repo: RunPostCommentRepository,
) -> list[Post]:
    """Load the posts for the feeds from run_posts (frozen run-start state)."""
    snapshots = run_post_repo.list_run_posts(run_id)
    run_post_ids = [s.run_post_id for s in snapshots]
    like_counts = run_post_like_repo.count_likes_by_run_post_ids(run_id, run_post_ids)
    reply_counts = run_post_comment_repo.count_comments_by_run_post_ids(
        run_id, run_post_ids
    )
    return [
        run_post_snapshot_to_post(
            s,
            like_count=like_counts.get(s.run_post_id, 0),
            reply_count=reply_counts.get(s.run_post_id, 0),
        )
        for s in snapshots
    ]


def load_seen_post_ids(
    *,
    agent: SimulationAgent,
    run_id: str,
    generated_feed_repo: GeneratedFeedRepository,
) -> set[str]:
    """Load the posts that the agent has already seen in the given run.

    Returns a set of post_ids.
    """
    if agent.agent_id is None:
        raise ValueError(
            "SimulationAgent.agent_id must be set to load seen post ids for a run"
        )
    return generated_feed_repo.get_post_ids_for_run(
        agent_id=agent.agent_id, run_id=run_id
    )


def filter_candidate_posts(
    *,
    candidate_posts: list[Post],
    agent: SimulationAgent,
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
    return [
        p
        for p in candidate_posts
        if p.post_id not in seen_post_ids and p.author_agent_id != agent.agent_id
    ]


def load_candidate_posts(
    *,
    agent: SimulationAgent,
    run_id: str,
    generated_feed_repo: GeneratedFeedRepository,
    run_post_repo: RunPostRepository,
    run_post_like_repo: RunPostLikeRepository,
    run_post_comment_repo: RunPostCommentRepository,
) -> list[Post]:
    """Load the candidate posts for the feeds from run_posts.

    Remove posts that:
    - The agent has already seen.
    - The agent themselves posted (or their original Bluesky profile posted)
    """
    candidate_posts: list[Post] = load_posts(
        run_id=run_id,
        run_post_repo=run_post_repo,
        run_post_like_repo=run_post_like_repo,
        run_post_comment_repo=run_post_comment_repo,
    )
    return filter_candidate_posts(
        candidate_posts=candidate_posts,
        agent=agent,
        run_id=run_id,
        generated_feed_repo=generated_feed_repo,
    )
