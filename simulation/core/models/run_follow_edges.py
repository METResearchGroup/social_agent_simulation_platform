"""Immutable snapshot of an internal follow edge at run start."""

from pydantic import BaseModel, ConfigDict, field_validator

from lib.validation_utils import validate_non_empty_string


class RunFollowEdgeSnapshot(BaseModel):
    """Frozen run-start follow relationship anchored to run membership."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    follower_agent_id: str
    target_agent_id: str
    created_at: str

    @field_validator(
        "run_id",
        "follower_agent_id",
        "target_agent_id",
        "created_at",
    )
    @classmethod
    def validate_text_fields(cls, value: str) -> str:
        return validate_non_empty_string(value)
