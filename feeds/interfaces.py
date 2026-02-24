"""Feed-generation port: abstract interface for generating feeds (lives next to implementation)."""

from abc import ABC, abstractmethod
from collections.abc import Mapping

from pydantic import JsonValue

from simulation.core.models.agents import SocialMediaAgent
from simulation.core.models.posts import BlueskyFeedPost


class FeedGenerator(ABC):
    """Abstract port for generating feeds for agents. Implementations live in feeds."""

    @abstractmethod
    def generate_feeds(
        self,
        agents: list[SocialMediaAgent],
        run_id: str,
        turn_number: int,
        feed_algorithm: str,
        feed_algorithm_config: Mapping[str, JsonValue] | None = None,
    ) -> dict[str, list[BlueskyFeedPost]]:
        """Generate feeds for all agents; returns mapping of agent handle to hydrated feed posts."""
        ...
