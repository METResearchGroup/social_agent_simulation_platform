from pydantic import BaseModel, field_validator

from lib.validation_utils import validate_non_empty_string
from simulation.core.models.actions import Comment
from simulation.core.models.generated.base import GenerationMetadata


class GeneratedComment(BaseModel):
    comment: Comment
    explanation: str
    metadata: GenerationMetadata

    @field_validator("comment")
    @classmethod
    def validate_comment(cls, v: Comment) -> Comment:
        if not v:
            raise ValueError("comment cannot be empty")
        return v

    @field_validator("explanation")
    @classmethod
    def validate_explanation(cls, v: str) -> str:
        return validate_non_empty_string(v, "explanation")

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, v: GenerationMetadata) -> GenerationMetadata:
        if not v:
            raise ValueError("metadata cannot be empty")
        return v
