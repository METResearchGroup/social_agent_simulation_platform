"""Agent linked agent domain model.

Agent-agent relationships (profile links).
"""

from pydantic import BaseModel, field_validator

from lib.validation_utils import validate_non_empty_string


class AgentLinkedAgent(BaseModel):
    """A link from one agent to another (by handle)."""

    agent_id: str
    linked_agent_handle: str

    @field_validator("agent_id")
    @classmethod
    def validate_agent_id(cls, v: str) -> str:
        return validate_non_empty_string(v, "agent_id")

    @field_validator("linked_agent_handle")
    @classmethod
    def validate_linked_agent_handle(cls, v: str) -> str:
        return validate_non_empty_string(v, "linked_agent_handle")
