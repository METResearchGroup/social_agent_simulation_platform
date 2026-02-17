from pydantic import BaseModel, field_validator

from lib.validation_utils import validate_non_empty_string


class Profile(BaseModel):
    """Base profile model - platform agnostic.

    This represents a social media profile that can be used to create agents.
    Platform-specific implementations can extend this with additional fields.
    """

    handle: str
    display_name: str
    bio: str
    followers_count: int
    follows_count: int
    posts_count: int

    @field_validator("handle")
    @classmethod
    def validate_handle(cls, v: str) -> str:
        return validate_non_empty_string(v, "handle")

    @field_validator("followers_count")
    @classmethod
    def validate_followers_count(cls, v: int) -> int:
        """Validate that followers_count is a non-negative integer."""
        if v < 0:
            raise ValueError("followers_count must be >= 0")
        return v

    @field_validator("follows_count")
    @classmethod
    def validate_follows_count(cls, v: int) -> int:
        """Validate that follows_count is a non-negative integer."""
        if v < 0:
            raise ValueError("follows_count must be >= 0")
        return v

    @field_validator("posts_count")
    @classmethod
    def validate_posts_count(cls, v: int) -> int:
        """Validate that posts_count is a non-negative integer."""
        if v < 0:
            raise ValueError("posts_count must be >= 0")
        return v


class BlueskyProfile(Profile):
    """Bluesky-specific profile with additional platform fields."""

    did: str  # Bluesky-specific decentralized identifier

    @field_validator("did")
    @classmethod
    def validate_did(cls, v: str) -> str:
        return validate_non_empty_string(v, "did")
