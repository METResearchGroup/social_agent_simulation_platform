"""Agent profile comment domain model.

User-entered comments (text + post URI) for an agent's profile history.
"""

from pydantic import BaseModel, field_validator

from lib.validation_utils import validate_non_empty_string


class AgentProfileComment(BaseModel):
    """A comment on a post, entered as part of an agent's profile history."""

    id: str
    agent_id: str
    post_uri: str
    text: str
    created_at: str
    updated_at: str

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        return validate_non_empty_string(v, "id")

    @field_validator("agent_id")
    @classmethod
    def validate_agent_id(cls, v: str) -> str:
        return validate_non_empty_string(v, "agent_id")
