"""Durable pre-run seed-state comments anchored to `agent_posts`.

These rows are mutable seed-state facts and are snapshotted into
`run_post_comments` at run creation time.
"""

from pydantic import BaseModel, ConfigDict, field_validator

from lib.validation_utils import validate_non_empty_string


class AgentPostComment(BaseModel):
    """Row-level seed-state comment on an agent-owned post."""

    model_config = ConfigDict(frozen=True)

    agent_post_comment_id: str
    agent_post_id: str
    author_agent_id: str
    body_text: str
    published_at: str
    created_at: str
    updated_at: str

    @field_validator(
        "agent_post_comment_id",
        "agent_post_id",
        "author_agent_id",
        "body_text",
        "published_at",
        "created_at",
        "updated_at",
    )
    @classmethod
    def validate_text_fields(cls, value: str) -> str:
        return validate_non_empty_string(value)
