from enum import Enum

from pydantic import BaseModel, ValidationInfo, field_validator

from lib.validation_utils import validate_non_empty_string


def _field_name(info: ValidationInfo | None) -> str:
    return getattr(info, "field_name", None) or "field"


class Like(BaseModel):
    like_id: str
    agent_id: str
    post_id: str
    created_at: str

    @field_validator("like_id", "agent_id", "post_id", mode="before")
    @classmethod
    def validate_identifier_fields(cls, v: str, info: ValidationInfo) -> str:
        """Validate that identifier fields are non-empty strings."""
        return validate_non_empty_string(v, _field_name(info))


class Comment(BaseModel):
    comment_id: str
    agent_id: str
    post_id: str
    created_at: str

    @field_validator("comment_id", "agent_id", "post_id", mode="before")
    @classmethod
    def validate_identifier_fields(cls, v: str, info: ValidationInfo) -> str:
        """Validate that identifier fields are non-empty strings."""
        return validate_non_empty_string(v, _field_name(info))


class Follow(BaseModel):
    follow_id: str
    agent_id: str
    user_id: str
    created_at: str

    @field_validator("follow_id", "agent_id", "user_id", mode="before")
    @classmethod
    def validate_identifier_fields(cls, v: str, info: ValidationInfo) -> str:
        """Validate that identifier fields are non-empty strings."""
        return validate_non_empty_string(v, _field_name(info))


class TurnAction(str, Enum):
    """Action types for a simulation turn."""

    LIKE = "like"
    COMMENT = "comment"
    FOLLOW = "follow"
