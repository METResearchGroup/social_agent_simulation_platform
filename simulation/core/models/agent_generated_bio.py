"""Versioned AI-generated bio tied to a user-created agent."""

from pydantic import BaseModel, field_validator

from lib.validation_utils import validate_non_empty_string, validate_not_none
from simulation.core.models.generated.base import GenerationMetadata


class AgentGeneratedBio(BaseModel):
    """Represent an AI-generated bio for a simulation agent."""

    id: str
    agent_id: str
    generated_bio: str
    metadata: GenerationMetadata

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        return validate_non_empty_string(value, "id")

    @field_validator("agent_id")
    @classmethod
    def validate_agent_id(cls, value: str) -> str:
        return validate_non_empty_string(value, "agent_id")

    @field_validator("generated_bio")
    @classmethod
    def validate_generated_bio(cls, value: str) -> str:
        return validate_non_empty_string(value, "generated_bio")

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, value: GenerationMetadata) -> GenerationMetadata:
        return validate_not_none(value, "metadata")
