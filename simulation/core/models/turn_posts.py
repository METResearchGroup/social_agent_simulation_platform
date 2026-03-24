"""Immutable snapshot of a turn-authored post row in ``turn_posts``."""

from pydantic import BaseModel, ConfigDict, field_validator

from lib.validation_utils import validate_non_empty_string


class TurnPostSnapshot(BaseModel):
    """Frozen snapshot for one post authored during a turn."""

    model_config = ConfigDict(frozen=True)

    turn_post_id: str
    run_id: str
    turn_number: int
    author_agent_id: str
    author_handle_at_time: str
    author_display_name_at_time: str
    body_text: str
    created_at: str
    explanation: str | None = None
    model_used: str | None = None
    generation_metadata_json: str | None = None
    generation_created_at: str | None = None

    @field_validator(
        "turn_post_id",
        "run_id",
        "author_agent_id",
        "author_handle_at_time",
        "author_display_name_at_time",
        "body_text",
        "created_at",
    )
    @classmethod
    def validate_required_text_fields(cls, value: str) -> str:
        return validate_non_empty_string(value)

    @field_validator("turn_number")
    @classmethod
    def validate_turn_number(cls, value: int) -> int:
        if value < 0:
            raise ValueError("turn_number must be non-negative")
        return value
