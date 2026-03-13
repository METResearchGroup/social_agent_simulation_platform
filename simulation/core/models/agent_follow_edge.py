"""Domain model for editable pre-run agent follow edges."""

from pydantic import BaseModel, field_validator

from lib.validation_utils import validate_non_empty_string


class AgentFollowEdge(BaseModel):
    """Durable seed-state row describing one internal agent-to-agent follow edge."""

    agent_follow_edge_id: str
    follower_agent_id: str
    target_agent_id: str
    created_at: str

    @field_validator("agent_follow_edge_id")
    @classmethod
    def validate_agent_follow_edge_id(cls, v: str) -> str:
        return validate_non_empty_string(v)

    @field_validator("follower_agent_id")
    @classmethod
    def validate_follower_agent_id(cls, v: str) -> str:
        return validate_non_empty_string(v)

    @field_validator("target_agent_id")
    @classmethod
    def validate_target_agent_id(cls, v: str) -> str:
        return validate_non_empty_string(v)
