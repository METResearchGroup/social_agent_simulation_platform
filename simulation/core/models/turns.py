"""Turn-related models for simulation results."""

from typing import Any

from pydantic import BaseModel, Field, field_validator

from lib.validation_utils import validate_non_empty_string, validate_nonnegative_value
from simulation.core.models.actions import TurnAction
from simulation.core.models.feeds import GeneratedFeed


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
        return validate_non_empty_string(v)

    @field_validator("turn_number")
    @classmethod
    def validate_turn_number(cls, v: int) -> int:
        """Validate that turn_number is non-negative."""
        return validate_nonnegative_value(v, "turn_number")

    model_config = {"frozen": True}  # Make immutable


class TurnData(BaseModel):
    """Complete turn data with feeds and posts.

    ``feeds`` and ``actions`` map canonical ``agent_id`` strings to per-agent data.
    ``feed_records`` holds the persisted ``GeneratedFeed`` row for each agent that
    had a feed on this turn (aligned with ``feeds`` keys). Display handles live on
    nested models, not in dict keys.
    """

    turn_number: int
    agents: list[Any]  # SimulationAgent - using Any to avoid circular import
    feeds: dict[str, list[Any]]  # agent_id -> list[Post]
    feed_records: dict[str, GeneratedFeed] = Field(default_factory=dict)
    actions: dict[
        str, list[Any]
    ]  # agent_id -> list[GeneratedLike | GeneratedComment | GeneratedFollow]

    @field_validator("turn_number")
    @classmethod
    def validate_turn_number(cls, v: int) -> int:
        """Validate that turn_number is non-negative."""
        return validate_nonnegative_value(v, "turn_number")

    model_config = {"frozen": True}  # Make immutable
