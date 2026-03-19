"""Durable pre-run seed-state like anchored to `agent_posts`.

This table represents "likes that already exist before a run starts".
They are editable/mutable seed-state facts and are snapshotted into
`run_post_likes` at run creation time.
"""

from pydantic import BaseModel, ConfigDict, field_validator

from lib.validation_utils import validate_non_empty_string


class AgentPostLike(BaseModel):
    """Row-level immutable-identity seed-state like."""

    model_config = ConfigDict(frozen=True)

    agent_post_like_id: str
    agent_post_id: str
    liker_agent_id: str
    created_at: str

    @field_validator(
        "agent_post_like_id",
        "agent_post_id",
        "liker_agent_id",
        "created_at",
    )
    @classmethod
    def validate_text_fields(cls, value: str) -> str:
        return validate_non_empty_string(value)
