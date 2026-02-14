# TODO: for now, we support only Bluesky posts being added to feeds.
# We'll revisit how to add AI-generated posts to feeds later on.
import uuid

from pydantic import BaseModel, field_validator

from simulation.core.models.validators import (
    validate_non_empty_string,
)
from simulation.core.models.validators import (
    validate_turn_number as validate_turn_number_core,
)


class GeneratedFeed(BaseModel):
    """A feed generated for an AI agent."""

    feed_id: str
    run_id: str
    turn_number: int
    agent_handle: str
    post_uris: list[str]
    created_at: str

    @field_validator("agent_handle")
    @classmethod
    def validate_agent_handle(cls, v: str) -> str:
        """Validate that agent_handle is a non-empty string."""
        return validate_non_empty_string(v, "agent_handle")

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, v: str) -> str:
        """Validate that run_id is a non-empty string."""
        return validate_non_empty_string(v, "run_id")

    @field_validator("feed_id")
    @classmethod
    def validate_feed_id(cls, v: str) -> str:
        """Validate that feed_id is a non-empty string."""
        return validate_non_empty_string(v, "feed_id")

    @field_validator("turn_number")
    @classmethod
    def validate_turn_number(cls, v: int) -> int:
        """Validate that turn_number is a non-negative integer."""
        validate_turn_number_core(v)
        return v

    @classmethod
    def generate_feed_id(cls) -> str:
        return f"feed_{str(uuid.uuid4())}"
