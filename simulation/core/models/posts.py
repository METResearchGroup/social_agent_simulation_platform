from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ValidationInfo, field_validator, model_validator

from lib.validation_utils import validate_non_empty_string, validate_nonnegative_value
from simulation.core.models.run_posts import RunPostSnapshot
from simulation.core.models.turn_posts import TurnPostSnapshot


class PostSource(str, Enum):
    """Source platform/type for a post."""

    BLUESKY = "bluesky"
    AI_GENERATED = "ai_generated"
    SEED_STATE = "seed_state"


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
    author_agent_id: str
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
        "author_agent_id",
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

        # SEED_STATE: post_id is run_post_id; uri is "seed_state:{run_post_id}"
        if source is PostSource.SEED_STATE:
            if "post_id" not in data:
                # uri format: "seed_state:{run_post_id}" -> post_id = run_post_id
                if cleaned_uri.startswith("seed_state:"):
                    data["post_id"] = cleaned_uri[len("seed_state:") :]
                else:
                    data["post_id"] = canonical_post_id(source=source, uri=cleaned_uri)
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


def run_post_snapshot_to_post(
    snapshot: RunPostSnapshot,
    *,
    like_count: int = 0,
    reply_count: int = 0,
) -> Post:
    """Map RunPostSnapshot to Post using run-scoped identity semantics.

    Uses post_id=run_post_id and uri=f"seed_state:{run_post_id}" so
    generated_feeds.post_ids can be hydrated from run_posts deterministically.
    Copies author/content/published fields from *_at_start. Baseline engagement
    counters use seeded snapshot counts for likes and comments at run start.
    """
    return Post(
        post_id=snapshot.run_post_id,
        source=PostSource.SEED_STATE,
        uri=f"seed_state:{snapshot.run_post_id}",
        author_agent_id=snapshot.author_agent_id,
        author_handle=snapshot.author_handle_at_start,
        author_display_name=snapshot.author_display_name_at_start,
        text=snapshot.body_text_at_start,
        created_at=snapshot.published_at_start,
        bookmark_count=0,
        like_count=like_count,
        quote_count=0,
        reply_count=reply_count,
        repost_count=0,
    )


def turn_post_snapshot_to_post(snapshot: TurnPostSnapshot) -> Post:
    """Map TurnPostSnapshot to Post for feed-visible ``turn_post_id`` IDs.

    Uses ``post_id=turn_post_id`` and ``uri=seed_state:{turn_post_id}`` so
    turn feed post_ids hydrate consistently with run-scoped seed posts.
    Turn-scoped engagement is not stored on run_post_* tables; like/reply
    counts are zero until turn-scoped engagement exists.
    """
    return Post(
        post_id=snapshot.turn_post_id,
        source=PostSource.SEED_STATE,
        uri=f"seed_state:{snapshot.turn_post_id}",
        author_agent_id=snapshot.author_agent_id,
        author_handle=snapshot.author_handle_at_time,
        author_display_name=snapshot.author_display_name_at_time,
        text=snapshot.body_text,
        created_at=snapshot.created_at,
        bookmark_count=0,
        like_count=0,
        quote_count=0,
        reply_count=0,
        repost_count=0,
    )
