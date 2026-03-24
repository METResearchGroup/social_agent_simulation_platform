from pydantic import BaseModel, field_validator

from lib.validation_utils import validate_non_empty_string, validate_not_none
from simulation.core.models.generated.base import GenerationMetadata
from simulation.core.models.turn_posts import TurnPostSnapshot


class GeneratedPost(BaseModel):
    """Turn-authored post produced during simulation (pre-persistence)."""

    snapshot: TurnPostSnapshot
    explanation: str
    metadata: GenerationMetadata

    @field_validator("snapshot")
    @classmethod
    def validate_snapshot(cls, v: TurnPostSnapshot) -> TurnPostSnapshot:
        return validate_not_none(v, "snapshot")

    @field_validator("explanation")
    @classmethod
    def validate_explanation(cls, v: str) -> str:
        return validate_non_empty_string(v)

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, v: GenerationMetadata) -> GenerationMetadata:
        return validate_not_none(v, "metadata")
