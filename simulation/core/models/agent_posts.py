"""Editable seed-state post authored by an internal agent.

This table represents the canonical, mutable "starting posts" state used to seed
future run snapshots. It is intentionally decoupled from feed_posts, which is
treated as an ingest/import catalog.
"""

from pydantic import BaseModel, ConfigDict, field_validator

from lib.validation_utils import validate_non_empty_string


class AgentPost(BaseModel):
    """Durable pre-run post stored as a row-level fact."""

    model_config = ConfigDict(frozen=True)

    agent_post_id: str
    agent_id: str
    body_text: str
    published_at: str
    created_at: str
    updated_at: str

    source_post_id: str | None = None
    source: str | None = None
    source_uri: str | None = None
    imported_author_handle: str | None = None
    imported_author_display_name: str | None = None
    import_metadata_json: str | None = None

    @field_validator(
        "agent_post_id",
        "agent_id",
        "body_text",
        "published_at",
        "created_at",
        "updated_at",
    )
    @classmethod
    def validate_required_text_fields(cls, value: str) -> str:
        return validate_non_empty_string(value)
