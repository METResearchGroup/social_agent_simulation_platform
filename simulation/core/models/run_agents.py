"""Immutable snapshot of an agent's membership in a run."""

from pydantic import BaseModel, ConfigDict, field_validator

from lib.validation_utils import (
    validate_non_empty_string,
    validate_nonnegative_value,
)


class RunAgentSnapshot(BaseModel):
    """Frozen run-start snapshot for one selected agent."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    agent_id: str
    selection_order: int
    handle_at_start: str
    display_name_at_start: str
    persona_bio_at_start: str
    followers_count_at_start: int
    follows_count_at_start: int
    posts_count_at_start: int
    created_at: str

    @field_validator(
        "run_id",
        "agent_id",
        "handle_at_start",
        "display_name_at_start",
        "persona_bio_at_start",
        "created_at",
    )
    @classmethod
    def validate_text_fields(cls, value: str) -> str:
        return validate_non_empty_string(value)

    @field_validator("selection_order")
    @classmethod
    def validate_selection_order(cls, value: int) -> int:
        return validate_nonnegative_value(value, "selection_order")

    @field_validator(
        "followers_count_at_start",
        "follows_count_at_start",
        "posts_count_at_start",
    )
    @classmethod
    def validate_count_fields(cls, value: int, info) -> int:
        return validate_nonnegative_value(value, str(info.field_name))
