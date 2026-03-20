"""Agent domain model for simulation agents."""

from enum import Enum

from pydantic import BaseModel, ValidationInfo, field_validator

from lib.agent_id import is_canonical_agent_id
from lib.validation_utils import validate_non_empty_string


class PersonaSource(str, Enum):
    """Source of the agent persona."""

    USER_GENERATED = "user_generated"
    SYNC_BLUESKY = "sync_bluesky"


class Agent(BaseModel):
    """Simulation agent with persona source and display info."""

    agent_id: str
    handle: str
    persona_source: PersonaSource
    display_name: str
    created_at: str
    updated_at: str

    @field_validator("agent_id")
    @classmethod
    def validate_agent_id(cls, v: str, info: ValidationInfo) -> str:
        cleaned = validate_non_empty_string(v)
        if is_canonical_agent_id(cleaned):
            return cleaned

        # Keep reads rollout-safe for legacy persisted IDs until full migration.
        strict_mode = bool(
            info.context and info.context.get("enforce_canonical_agent_id", False)
        )
        if strict_mode:
            raise ValueError("agent_id must match ^[0-9a-f]{16}$")
        return cleaned

    @field_validator("handle")
    @classmethod
    def validate_handle(cls, v: str) -> str:
        return validate_non_empty_string(v)

    @field_validator("persona_source", mode="before")
    @classmethod
    def validate_persona_source(cls, v: object) -> PersonaSource:
        if not isinstance(v, PersonaSource):
            raise ValueError(
                f"persona_source must be a PersonaSource enum, got {type(v).__name__}"
            )
        return v
