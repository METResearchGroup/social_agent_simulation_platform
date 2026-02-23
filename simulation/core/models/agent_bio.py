"""Agent persona bio domain model."""

from enum import Enum

from pydantic import BaseModel, field_validator

from lib.validation_utils import validate_non_empty_string


class PersonaBioSource(str, Enum):
    """Source of the persona bio text."""

    AI_GENERATED = "ai_generated"
    USER_PROVIDED = "user_provided"


class AgentBio(BaseModel):
    """Persona bio for an agent; supports multiple versions per agent."""

    id: str
    agent_id: str
    persona_bio: str
    persona_bio_source: PersonaBioSource
    created_at: str
    updated_at: str

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        return validate_non_empty_string(v, "id")

    @field_validator("agent_id")
    @classmethod
    def validate_agent_id(cls, v: str) -> str:
        return validate_non_empty_string(v, "agent_id")

    @field_validator("persona_bio")
    @classmethod
    def validate_persona_bio(cls, v: str) -> str:
        return validate_non_empty_string(v, "persona_bio")

    @field_validator("persona_bio_source", mode="before")
    @classmethod
    def validate_persona_bio_source(cls, v: object) -> PersonaBioSource:
        if not isinstance(v, PersonaBioSource):
            raise ValueError(
                f"persona_bio_source must be a PersonaBioSource enum, got {type(v).__name__}"
            )
        return v
