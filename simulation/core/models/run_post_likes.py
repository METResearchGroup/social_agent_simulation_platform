"""Immutable run-start snapshot of likes anchored to run_posts.

These rows are snapshotted during run creation from `agent_post_likes`,
filtered by the selected run's `run_agents` membership and the selected
run's `run_posts` rows.
"""

from pydantic import BaseModel, ConfigDict, field_validator

from lib.validation_utils import validate_non_empty_string


class RunPostLikeSnapshot(BaseModel):
    """Frozen run-start like snapshot."""

    model_config = ConfigDict(frozen=True)

    run_post_like_id: str
    run_id: str
    run_post_id: str
    liker_agent_id: str
    liker_handle_at_start: str
    liker_display_name_at_start: str
    created_at: str

    @field_validator(
        "run_post_like_id",
        "run_id",
        "run_post_id",
        "liker_agent_id",
        "liker_handle_at_start",
        "liker_display_name_at_start",
        "created_at",
    )
    @classmethod
    def validate_text_fields(cls, value: str) -> str:
        return validate_non_empty_string(value)
