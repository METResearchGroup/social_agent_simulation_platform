"""Agent domain model for simulation agents."""

from enum import Enum

from pydantic import BaseModel, field_validator

from lib.validation_utils import validate_non_empty_string


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
    def validate_persona_source(cls, v: object) -> PersonaSource:
        if not isinstance(v, PersonaSource):
            raise ValueError(
                f"persona_source must be a PersonaSource enum, got {type(v).__name__}"
            )
        return v
