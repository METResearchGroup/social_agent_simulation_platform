"""Adapter that implements FeedGenerator by delegating to the existing generate_feeds function."""

from collections.abc import Mapping

from pydantic import JsonValue

from db.repositories.interfaces import (
    GeneratedFeedRepository,
    RunPostCommentRepository,
    RunPostLikeRepository,
    RunPostRepository,
)
from feeds.feed_generator import generate_feeds as generate_feeds_impl
from feeds.interfaces import FeedGenerator
from simulation.core.models.agents import SimulationAgent
from simulation.core.models.posts import Post


class FeedGeneratorAdapter(FeedGenerator):
    """Implements FeedGenerator."""

    def __init__(
        self,
        *,
        generated_feed_repo: GeneratedFeedRepository,
        run_post_repo: RunPostRepository,
        run_post_like_repo: RunPostLikeRepository,
        run_post_comment_repo: RunPostCommentRepository,
    ) -> None:
        self._generated_feed_repo = generated_feed_repo
        self._run_post_repo = run_post_repo
        self._run_post_like_repo = run_post_like_repo
        self._run_post_comment_repo = run_post_comment_repo

    def generate_feeds(
        self,
        agents: list[SimulationAgent],
        run_id: str,
        turn_number: int,
        feed_algorithm: str,
        feed_algorithm_config: Mapping[str, JsonValue] | None = None,
    ) -> dict[str, list[Post]]:
        return generate_feeds_impl(
            agents=agents,
            run_id=run_id,
            turn_number=turn_number,
            generated_feed_repo=self._generated_feed_repo,
            feed_algorithm=feed_algorithm,
            run_post_repo=self._run_post_repo,
            run_post_like_repo=self._run_post_like_repo,
            run_post_comment_repo=self._run_post_comment_repo,
            feed_algorithm_config=feed_algorithm_config,
        )
