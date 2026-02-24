"""Agent liked post domain model.

User-entered liked post URIs for an agent's profile history.
"""

from pydantic import BaseModel, field_validator

from lib.validation_utils import validate_non_empty_string


class AgentLikedPost(BaseModel):
    """A post URI that an agent has liked (profile history)."""

    agent_id: str
    post_uri: str

    @field_validator("agent_id")
    @classmethod
    def validate_agent_id(cls, v: str) -> str:
        return validate_non_empty_string(v, "agent_id")

    @field_validator("post_uri")
    @classmethod
    def validate_post_uri(cls, v: str) -> str:
        return validate_non_empty_string(v, "post_uri")
