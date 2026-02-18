"""Turn-related models for simulation results."""

from pydantic import BaseModel, field_validator

from lib.validation_utils import validate_non_empty_string, validate_nonnegative_value
from simulation.core.models.actions import TurnAction
from simulation.core.models.agents import SocialMediaAgent
from simulation.core.models.generated.comment import GeneratedComment
from simulation.core.models.generated.follow import GeneratedFollow
from simulation.core.models.generated.like import GeneratedLike
from simulation.core.models.posts import BlueskyFeedPost


class TurnResult(BaseModel):
    """Result of executing a single simulation turn.

    Contains aggregated statistics about agent actions during the turn.

    Attributes:
        turn_number: The turn number (0-indexed).
        total_actions: Dictionary mapping action types to counts.
        execution_time_ms: Optional execution time in milliseconds.
    """

    turn_number: int
    total_actions: dict[TurnAction, int]
    execution_time_ms: int | None = None

    @field_validator("turn_number")
    @classmethod
    def validate_turn_number(cls, v: int) -> int:
        """Validate that turn_number is non-negative."""
        return validate_nonnegative_value(v, "turn_number")

    model_config = {"frozen": True}  # Make immutable


class TurnMetadata(BaseModel):
    """Metadata for a simulation turn.

    Contains basic information about a turn without the full data.
    """

    run_id: str
    turn_number: int
    total_actions: dict[TurnAction, int]
    created_at: str

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, v: str) -> str:
        """Validate that run_id is a non-empty string."""
        return validate_non_empty_string(v, "run_id")

    @field_validator("turn_number")
    @classmethod
    def validate_turn_number(cls, v: int) -> int:
        """Validate that turn_number is non-negative."""
        return validate_nonnegative_value(v, "turn_number")

    model_config = {"frozen": True}  # Make immutable


class TurnData(BaseModel):
    """Complete turn data with feeds and posts.

    Contains all the data for a single turn, including the feeds and posts.
    """

    turn_number: int
    agents: list[SocialMediaAgent]
    feeds: dict[str, list[BlueskyFeedPost]]
    actions: dict[str, list[GeneratedLike | GeneratedComment | GeneratedFollow]]

    @field_validator("turn_number")
    @classmethod
    def validate_turn_number(cls, v: int) -> int:
        """Validate that turn_number is non-negative."""
        return validate_nonnegative_value(v, "turn_number")

    model_config = {"frozen": True, "arbitrary_types_allowed": True}
