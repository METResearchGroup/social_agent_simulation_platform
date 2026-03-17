"""Editable seed-state follow edge between two internal agents."""

from pydantic import BaseModel, ConfigDict, field_validator

from lib.validation_utils import validate_non_empty_string


class AgentFollowEdge(BaseModel):
    """Durable pre-run follow edge stored as a row-level fact."""

    model_config = ConfigDict(frozen=True)

    agent_follow_edge_id: str
    follower_agent_id: str
    target_agent_id: str
    created_at: str

    @field_validator(
        "agent_follow_edge_id",
        "follower_agent_id",
        "target_agent_id",
        "created_at",
    )
    @classmethod
    def validate_text_fields(cls, value: str) -> str:
        return validate_non_empty_string(value)
