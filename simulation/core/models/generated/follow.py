from pydantic import BaseModel, field_validator

from lib.validation_utils import validate_non_empty_string, validate_not_none
from simulation.core.models.actions import Follow
from simulation.core.models.generated.base import GenerationMetadata


class GeneratedFollow(BaseModel):
    follow: Follow
    explanation: str
    metadata: GenerationMetadata

    @field_validator("follow")
    @classmethod
    def validate_follow(cls, v: Follow) -> Follow:
        return validate_not_none(v, "follow")

    @field_validator("explanation")
    @classmethod
    def validate_explanation(cls, v: str) -> str:
        return validate_non_empty_string(v, "explanation")

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, v: GenerationMetadata) -> GenerationMetadata:
        return validate_not_none(v, "metadata")
