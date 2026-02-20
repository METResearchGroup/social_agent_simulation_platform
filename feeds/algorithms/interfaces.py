"""Abstract interfaces for feed generation algorithms."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, TypedDict

from pydantic import BaseModel

if TYPE_CHECKING:
    from simulation.core.models.agents import SocialMediaAgent
    from simulation.core.models.posts import BlueskyFeedPost


class FeedAlgorithmMetadata(TypedDict, total=False):
    """Metadata for a feed algorithm, exposed to the API and UI."""

    display_name: str
    description: str
    config_schema: dict[str, Any] | None


class FeedAlgorithmResult(BaseModel):
    """Result of a feed ranking algorithm.

    post_uris is ordered: first element = top of feed. Implementations must use
    deterministic tie-breaking when scores/keys are equal.
    """

    feed_id: str
    agent_handle: str
    post_uris: list[str]


class FeedAlgorithm(ABC):
    """Abstract interface for feed ranking algorithms. Implementations must be deterministic."""

    @property
    @abstractmethod
    def metadata(self) -> FeedAlgorithmMetadata:
        """Algorithm metadata for API and UI exposure."""
        ...

    @abstractmethod
    def generate(
        self,
        *,
        candidate_posts: list[
            BlueskyFeedPost
        ],  # TODO: decouple from Bluesky-specific type
        agent: SocialMediaAgent,
        limit: int,
    ) -> FeedAlgorithmResult:
        """Rank and select posts.

        Return post_uris in feed display order. Use deterministic tie-breaking
        (e.g. uri) when primary sort keys tie.
        """
        ...
