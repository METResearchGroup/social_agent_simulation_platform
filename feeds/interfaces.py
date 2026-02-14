"""Feed-generation port: abstract interface for generating feeds (lives next to implementation)."""

from abc import ABC, abstractmethod

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
    ) -> dict[str, list[BlueskyFeedPost]]:
        """Generate feeds for all agents; returns mapping of agent handle to hydrated feed posts."""
        ...
