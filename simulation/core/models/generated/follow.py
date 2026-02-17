from pydantic import BaseModel, field_validator

from simulation.core.models.actions import Follow
from simulation.core.models.generated.base import GenerationMetadata


class GeneratedFollow(BaseModel):
    follow: Follow
    explanation: str
    metadata: GenerationMetadata

    @field_validator("follow")
    @classmethod
    def validate_follow(cls, v: Follow) -> Follow:
        if not v:
            raise ValueError("follow cannot be empty")
        return v

    @field_validator("explanation")
    @classmethod
    def validate_explanation(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("explanation cannot be empty")
        return v

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, v: GenerationMetadata) -> GenerationMetadata:
        if not v:
            raise ValueError("metadata cannot be empty")
        return v
