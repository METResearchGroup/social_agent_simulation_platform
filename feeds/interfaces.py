"""Feed-generation port: abstract interface for generating feeds (lives next to implementation)."""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass

from pydantic import JsonValue

from simulation.core.models.agents import SimulationAgent
from simulation.core.models.feeds import GeneratedFeed
from simulation.core.models.posts import Post


@dataclass(frozen=True, slots=True)
class FeedGenerationResult:
    """Turn feed artifacts produced before persistence.

    - ``generated_feeds_by_agent`` is used for turn persistence.
    - ``hydrated_feeds_by_agent`` is used for downstream action generation.
    """

    generated_feeds_by_agent: dict[str, GeneratedFeed]
    hydrated_feeds_by_agent: dict[str, list[Post]]


class FeedGenerator(ABC):
    """Abstract port for generating feeds for agents. Implementations live in feeds."""

    @abstractmethod
    def generate_feeds(
        self,
        agents: list[SimulationAgent],
        run_id: str,
        turn_number: int,
        feed_algorithm: str,
        feed_algorithm_config: Mapping[str, JsonValue] | None = None,
    ) -> FeedGenerationResult:
        """Generate feed artifacts for all agents without persistence side effects."""
        ...
