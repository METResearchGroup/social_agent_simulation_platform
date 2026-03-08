from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ValidationInfo, field_validator, model_validator

from lib.validation_utils import validate_non_empty_string, validate_nonnegative_value


class PostSource(str, Enum):
    """Source platform/type for a post."""

    BLUESKY = "bluesky"
    AI_GENERATED = "ai_generated"


def canonical_post_id(*, source: PostSource, uri: str) -> str:
    """Return canonical post_id for a source-native uri.

    Format: "{source}:{uri}".
    """

    return f"{source.value}:{uri}"


class Post(BaseModel):
    """Platform-agnostic social media post with canonical identifiers."""

    post_id: str
    source: PostSource
    uri: str
    author_handle: str
    author_display_name: str
    text: str
    bookmark_count: int
    like_count: int
    quote_count: int
    reply_count: int
    repost_count: int
    created_at: str

    @field_validator(
        "post_id",
        "uri",
        "author_handle",
        "author_display_name",
        "created_at",
        mode="before",
    )
    @classmethod
    def validate_required_strings(cls, v: object) -> str:
        # Uses shared helper so error messages are consistent across models/tests.
        return validate_non_empty_string(v)  # pyright: ignore[reportArgumentType]

    @field_validator("text", mode="before")
    @classmethod
    def validate_text_preserve_whitespace(cls, v: object) -> str:
        # Preserve the raw text (including leading/trailing whitespace) while still
        # rejecting values that are empty/whitespace-only.
        if v is None:
            raise ValueError("value cannot be None")
        if not isinstance(v, str):
            raise ValueError("value must be a string")
        if v.strip() == "":
            raise ValueError("value cannot be empty")
        return v

    @field_validator("source", mode="before")
    @classmethod
    def validate_source(cls, v: object) -> PostSource:
        if not isinstance(v, PostSource):
            raise ValueError(
                f"source must be a PostSource enum, got {type(v).__name__}"
            )
        return v

    @field_validator(
        "bookmark_count",
        "like_count",
        "quote_count",
        "reply_count",
        "repost_count",
        mode="before",
    )
    @classmethod
    def validate_count_fields(cls, v: int, info: ValidationInfo) -> int:
        field_name = getattr(info, "field_name", None) or "field"
        return int(validate_nonnegative_value(v, field_name))

    @model_validator(mode="before")
    @classmethod
    def set_and_validate_post_id(cls, data: object) -> object:
        """Set post_id from (source, uri) if missing and validate canonical format."""

        if not isinstance(data, dict):
            return data

        source = data.get("source")
        uri = data.get("uri")
        if not isinstance(source, PostSource) or not isinstance(uri, str):
            return data

        cleaned_uri = uri.strip()
        data["uri"] = cleaned_uri
        if cleaned_uri == "":
            return data

        expected = canonical_post_id(source=source, uri=cleaned_uri)

        if "post_id" not in data:
            data["post_id"] = expected
            return data

        post_id = data.get("post_id")
        if not isinstance(post_id, str):
            return data

        cleaned_post_id = post_id.strip()
        data["post_id"] = cleaned_post_id
        if cleaned_post_id != expected:
            raise ValueError(
                f"post_id must match canonical format '{expected}' for source+uri"
            )

        return data
