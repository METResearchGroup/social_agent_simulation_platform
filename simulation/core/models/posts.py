from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ValidationInfo, field_validator, model_validator

from lib.validation_utils import validate_non_empty_string, validate_nonnegative_value


class PostSource(str, Enum):
    """Source platform/type for a post."""

    BLUESKY = "bluesky"
    AI_GENERATED = "ai_generated"


def _field_name(info: ValidationInfo | None) -> str:
    return getattr(info, "field_name", None) or "field"


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

    @field_validator("post_id", "uri", "author_handle", mode="before")
    @classmethod
    def validate_identifier_fields(cls, v: str, info: ValidationInfo) -> str:
        return validate_non_empty_string(v, _field_name(info))

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
        return validate_nonnegative_value(v, _field_name(info))

    @model_validator(mode="before")
    @classmethod
    def set_and_validate_post_id(cls, data: dict) -> dict:
        """Set post_id from (source, uri) if missing and validate canonical format."""
        if not isinstance(data, dict):
            return data

        if "source" in data and "uri" in data:
            source = data["source"]
            uri = data["uri"]
            if isinstance(source, PostSource) and isinstance(uri, str):
                uri_stripped = uri.strip()
                data["uri"] = uri_stripped
                if uri_stripped == "":
                    return data

                expected = canonical_post_id(source=source, uri=uri_stripped)
                if "post_id" not in data:
                    data["post_id"] = expected
                elif isinstance(data["post_id"], str):
                    post_id_stripped = data["post_id"].strip()
                    data["post_id"] = post_id_stripped
                    if post_id_stripped != expected:
                        raise ValueError(
                            f"post_id must match canonical format '{expected}' for source+uri"
                        )

        return data
