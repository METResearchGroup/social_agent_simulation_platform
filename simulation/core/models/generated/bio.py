from pydantic import BaseModel, field_validator

from lib.validation_utils import validate_non_empty_string
from simulation.core.models.generated.base import GenerationMetadata


class GeneratedBio(BaseModel):
    """An AI-generated bio for a Bluesky profile."""

    handle: str
    generated_bio: str
    metadata: GenerationMetadata

    @field_validator("handle")
    @classmethod
    def validate_handle(cls, v: str) -> str:
        return validate_non_empty_string(v, "handle")

    @field_validator("generated_bio")
    @classmethod
    def validate_generated_bio(cls, v: str) -> str:
        return validate_non_empty_string(v, "generated_bio")

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, v: GenerationMetadata) -> GenerationMetadata:
        if not v:
            raise ValueError("metadata cannot be empty")
        return v
