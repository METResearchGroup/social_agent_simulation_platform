"""Abstract interfaces for action generators."""

from abc import ABC, abstractmethod

from simulation.core.models.generated.follow import GeneratedFollow
from simulation.core.models.generated.comment import GeneratedComment
from simulation.core.models.generated.like import GeneratedLike
from simulation.core.models.posts import BlueskyFeedPost


class LikeGenerator(ABC):
    """Abstract interface for generating likes from feed candidates."""

    @abstractmethod
    def generate(
        self,
        *,
        candidates: list[BlueskyFeedPost],
        run_id: str,
        turn_number: int,
        agent_handle: str,
    ) -> list[GeneratedLike]:
        """Generate likes from candidates."""
        ...


class FollowGenerator(ABC):
    """Abstract interface for generating follows from feed candidates."""
    @abstractmethod
    def generate(
        self,
        *,
        candidates: list[BlueskyFeedPost],
        run_id: str,
        turn_number: int,
        agent_handle: str,
    ) -> list[GeneratedFollow]:
        """Generate follows from candidates."""
        ...

class CommentGenerator(ABC):
    """Abstract interface for generating comments from feed candidates."""

    @abstractmethod
    def generate(
        self,
        *,
        candidates: list[BlueskyFeedPost],
        run_id: str,
        turn_number: int,
        agent_handle: str,
    ) -> list[GeneratedComment]:
        """Generate comments from candidates."""
        ...
