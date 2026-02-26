from __future__ import annotations

from pydantic import BaseModel, ValidationInfo, field_validator

from lib.validation_utils import validate_non_empty_string


def _field_name(info: ValidationInfo | None) -> str:
    return getattr(info, "field_name", None) or "field"


class AgentSeedLike(BaseModel):
    seed_like_id: str
    agent_handle: str
    post_uri: str
    created_at: str

    @field_validator(
        "seed_like_id", "agent_handle", "post_uri", "created_at", mode="before"
    )
    @classmethod
    def validate_required_fields(cls, v: str, info: ValidationInfo) -> str:
        return validate_non_empty_string(v, _field_name(info))


class AgentSeedComment(BaseModel):
    seed_comment_id: str
    agent_handle: str
    post_uri: str | None = None
    text: str
    created_at: str

    @field_validator(
        "seed_comment_id", "agent_handle", "text", "created_at", mode="before"
    )
    @classmethod
    def validate_required_fields(cls, v: str, info: ValidationInfo) -> str:
        return validate_non_empty_string(v, _field_name(info))


class AgentSeedFollow(BaseModel):
    seed_follow_id: str
    agent_handle: str
    user_id: str
    created_at: str

    @field_validator(
        "seed_follow_id", "agent_handle", "user_id", "created_at", mode="before"
    )
    @classmethod
    def validate_required_fields(cls, v: str, info: ValidationInfo) -> str:
        return validate_non_empty_string(v, _field_name(info))
