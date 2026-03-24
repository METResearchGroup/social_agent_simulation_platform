"""Turn-related models for simulation results."""

from typing import Any

from pydantic import BaseModel, field_validator

from lib.validation_utils import validate_non_empty_string, validate_nonnegative_value
from simulation.core.models.actions import TurnAction
from simulation.core.models.feeds import GeneratedFeed
from simulation.core.models.generated.comment import GeneratedComment
from simulation.core.models.generated.follow import GeneratedFollow
from simulation.core.models.generated.like import GeneratedLike
from simulation.core.models.generated.post import GeneratedPost
from simulation.core.models.posts import Post


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
    """Metadata for a simulation turn as stored in the ``turns`` table.

    One row per (run_id, turn_number). Contains basic information about a turn
    without feeds, actions, or metrics payloads.
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
    had a feed on this turn (aligned with ``feeds`` keys); those rows come from
    ``turn_generated_feeds`` at persistence time. Action lists are built from
    persisted turn-scoped like/comment/follow rows. Display handles live on
    nested models, not in dict keys.
    """

    turn_number: int
    agents: list[Any]  # SimulationAgent — Any avoids importing agents module here
    feeds: dict[str, list[Post]]
    feed_records: dict[str, GeneratedFeed]
    actions: dict[
        str,
        list[GeneratedLike | GeneratedComment | GeneratedFollow | GeneratedPost],
    ]

    @field_validator("turn_number")
    @classmethod
    def validate_turn_number(cls, v: int) -> int:
        """Validate that turn_number is non-negative."""
        return validate_nonnegative_value(v, "turn_number")

    model_config = {"frozen": True}  # Make immutable
