from pydantic import BaseModel, field_validator, model_validator

from lib.validation_utils import validate_non_empty_string


class Post(BaseModel):
    """Base post model - platform agnostic.

    This represents a social media post. Platform-specific implementations
    can extend this with additional fields.
    """

    id: str  # Generic identifier (could be URI, URL, UUID, etc.)
    author_handle: str
    author_display_name: str
    text: str
    like_count: int
    created_at: str

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        return validate_non_empty_string(v, "id")

    @field_validator("author_handle")
    @classmethod
    def validate_author_handle(cls, v: str) -> str:
        return validate_non_empty_string(v, "author_handle")


class BlueskyFeedPost(Post):
    """Bluesky-specific post with additional platform fields."""

    uri: str  # Bluesky-specific URI
    bookmark_count: int
    quote_count: int
    reply_count: int
    repost_count: int

    @field_validator("uri")
    @classmethod
    def validate_uri(cls, v: str) -> str:
        return validate_non_empty_string(v, "uri")

    @field_validator("bookmark_count")
    @classmethod
    def validate_bookmark_count(cls, v: int) -> int:
        """Validate that bookmark_count is non-negative."""
        if v < 0:
            raise ValueError("bookmark_count must be >= 0")
        return v

    @field_validator("quote_count")
    @classmethod
    def validate_quote_count(cls, v: int) -> int:
        """Validate that quote_count is non-negative."""
        if v < 0:
            raise ValueError("quote_count must be >= 0")
        return v

    @field_validator("reply_count")
    @classmethod
    def validate_reply_count(cls, v: int) -> int:
        """Validate that reply_count is non-negative."""
        if v < 0:
            raise ValueError("reply_count must be >= 0")
        return v

    @field_validator("repost_count")
    @classmethod
    def validate_repost_count(cls, v: int) -> int:
        """Validate that repost_count is non-negative."""
        if v < 0:
            raise ValueError("repost_count must be >= 0")
        return v

    @model_validator(mode="before")
    @classmethod
    def set_id_from_uri(cls, data: dict) -> dict:
        """Set id from uri if not provided."""
        if isinstance(data, dict) and "uri" in data and "id" not in data:
            data["id"] = data["uri"]
        return data
