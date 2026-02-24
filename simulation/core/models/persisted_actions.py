"""Persisted action row models for run-scoped likes, comments, follows.

These are pure data shapes used when reading/writing action tables.
No imports from db, feeds, or ai.
"""

from pydantic import BaseModel, field_validator

from lib.validation_utils import validate_nonnegative_value


class PersistedLike(BaseModel):
    """Row shape for a persisted like action."""

    like_id: str
    run_id: str
    turn_number: int
    agent_handle: str
    post_id: str
    created_at: str
    explanation: str | None = None
    model_used: str | None = None
    generation_metadata_json: str | None = None
    generation_created_at: str | None = None

    @field_validator("turn_number")
    @classmethod
    def validate_turn_number(cls, v: int) -> int:
        return validate_nonnegative_value(v, "turn_number")


class PersistedComment(BaseModel):
    """Row shape for a persisted comment action."""

    comment_id: str
    run_id: str
    turn_number: int
    agent_handle: str
    post_id: str
    text: str
    created_at: str
    explanation: str | None = None
    model_used: str | None = None
    generation_metadata_json: str | None = None
    generation_created_at: str | None = None

    @field_validator("turn_number")
    @classmethod
    def validate_turn_number(cls, v: int) -> int:
        return validate_nonnegative_value(v, "turn_number")


class PersistedFollow(BaseModel):
    """Row shape for a persisted follow action."""

    follow_id: str
    run_id: str
    turn_number: int
    agent_handle: str
    user_id: str
    created_at: str
    explanation: str | None = None
    model_used: str | None = None
    generation_metadata_json: str | None = None
    generation_created_at: str | None = None

    @field_validator("turn_number")
    @classmethod
    def validate_turn_number(cls, v: int) -> int:
        return validate_nonnegative_value(v, "turn_number")
