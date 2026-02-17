from pydantic import BaseModel, field_validator

from lib.validation_utils import validate_non_empty_string, validate_not_none
from simulation.core.models.actions import Like
from simulation.core.models.generated.base import GenerationMetadata


class GeneratedLike(BaseModel):
    like: Like
    explanation: str
    metadata: GenerationMetadata

    @field_validator("like")
    @classmethod
    def validate_like(cls, v: Like) -> Like:
        return validate_not_none(v, "like")

    @field_validator("explanation")
    @classmethod
    def validate_explanation(cls, v: str) -> str:
        return validate_non_empty_string(v, "explanation")

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, v: GenerationMetadata) -> GenerationMetadata:
        return validate_not_none(v, "metadata")
