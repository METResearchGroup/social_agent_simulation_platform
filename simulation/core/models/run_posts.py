"""Immutable snapshot of a post at run start."""

from pydantic import BaseModel, ConfigDict, field_validator

from lib.validation_utils import validate_non_empty_string


class RunPostSnapshot(BaseModel):
    """Frozen run-start snapshot for one post from agent_posts."""

    model_config = ConfigDict(frozen=True)

    run_post_id: str
    run_id: str
    agent_post_id: str
    author_agent_id: str
    author_handle_at_start: str
    author_display_name_at_start: str
    body_text_at_start: str
    published_at_start: str
    source_post_id_at_start: str | None = None
    source_at_start: str | None = None
    source_uri_at_start: str | None = None
    created_at: str

    @field_validator(
        "run_post_id",
        "run_id",
        "agent_post_id",
        "author_agent_id",
        "author_handle_at_start",
        "author_display_name_at_start",
        "body_text_at_start",
        "published_at_start",
        "created_at",
    )
    @classmethod
    def validate_required_text_fields(cls, value: str) -> str:
        return validate_non_empty_string(value)
