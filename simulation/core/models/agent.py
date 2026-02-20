"""Agent domain model for simulation agents."""

from enum import Enum

from pydantic import BaseModel, field_validator

from lib.validation_utils import validate_non_empty_string, validate_value_in_set


class PersonaSource(str, Enum):
    """Source of the agent persona."""

    USER_GENERATED = "user_generated"
    SYNC_BLUESKY = "sync_bluesky"


class Agent(BaseModel):
    """Simulation agent with persona source and display info."""

    agent_id: str
    handle: str
    persona_source: PersonaSource
    display_name: str
    created_at: str
    updated_at: str

    @field_validator("agent_id")
    @classmethod
    def validate_agent_id(cls, v: str) -> str:
        return validate_non_empty_string(v, "agent_id")

    @field_validator("handle")
    @classmethod
    def validate_handle(cls, v: str) -> str:
        return validate_non_empty_string(v, "handle")

    @field_validator("persona_source", mode="before")
    @classmethod
    def validate_persona_source(cls, v: str | PersonaSource) -> PersonaSource:
        if isinstance(v, PersonaSource):
            return v
        validated = validate_non_empty_string(str(v), "persona_source")
        validate_value_in_set(
            validated,
            "persona_source",
            {ps.value for ps in PersonaSource},
            allowed_display_name="user_generated, sync_bluesky",
        )
        return PersonaSource(validated)
