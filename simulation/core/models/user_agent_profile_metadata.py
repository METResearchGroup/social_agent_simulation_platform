"""User agent profile metadata domain model."""

from pydantic import BaseModel, field_validator

from lib.validation_utils import validate_non_empty_string, validate_nonnegative_value


class UserAgentProfileMetadata(BaseModel):
    """Profile counts (followers, follows, posts) for an agent."""

    id: str
    agent_id: str
    followers_count: int
    follows_count: int
    posts_count: int
    created_at: str
    updated_at: str

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        return validate_non_empty_string(v, "id")

    @field_validator("agent_id")
    @classmethod
    def validate_agent_id(cls, v: str) -> str:
        return validate_non_empty_string(v, "agent_id")

    @field_validator("followers_count")
    @classmethod
    def validate_followers_count(cls, v: int) -> int:
        return validate_nonnegative_value(v, "followers_count")

    @field_validator("follows_count")
    @classmethod
    def validate_follows_count(cls, v: int) -> int:
        return validate_nonnegative_value(v, "follows_count")

    @field_validator("posts_count")
    @classmethod
    def validate_posts_count(cls, v: int) -> int:
        return validate_nonnegative_value(v, "posts_count")
