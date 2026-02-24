"""Adapter that implements FeedGenerator by delegating to the existing generate_feeds function."""

from collections.abc import Mapping

from pydantic import JsonValue

from db.repositories.interfaces import FeedPostRepository, GeneratedFeedRepository
from feeds.feed_generator import generate_feeds as generate_feeds_impl
from feeds.interfaces import FeedGenerator
from simulation.core.models.agents import SocialMediaAgent
from simulation.core.models.posts import BlueskyFeedPost


class FeedGeneratorAdapter(FeedGenerator):
    """Implements FeedGenerator."""

    def __init__(
        self,
        *,
        generated_feed_repo: GeneratedFeedRepository,
        feed_post_repo: FeedPostRepository,
    ) -> None:
        self._generated_feed_repo = generated_feed_repo
        self._feed_post_repo = feed_post_repo

    def generate_feeds(
        self,
        agents: list[SocialMediaAgent],
        run_id: str,
        turn_number: int,
        feed_algorithm: str,
        feed_algorithm_config: Mapping[str, JsonValue] | None = None,
    ) -> dict[str, list[BlueskyFeedPost]]:
        return generate_feeds_impl(
            agents=agents,
            run_id=run_id,
            turn_number=turn_number,
            generated_feed_repo=self._generated_feed_repo,
            feed_post_repo=self._feed_post_repo,
            feed_algorithm=feed_algorithm,
            feed_algorithm_config=feed_algorithm_config,
        )
