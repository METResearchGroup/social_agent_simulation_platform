"""Immutable run-start snapshot of comments anchored to run_posts.

These rows are snapshotted during run creation from `agent_post_comments`,
filtered by the selected run's `run_agents` membership and the selected
run's `run_posts` rows.
"""

from pydantic import BaseModel, ConfigDict, field_validator

from lib.validation_utils import validate_non_empty_string


class RunPostCommentSnapshot(BaseModel):
    """Frozen run-start comment snapshot."""

    model_config = ConfigDict(frozen=True)

    run_post_comment_id: str
    run_id: str
    run_post_id: str
    author_agent_id: str
    author_handle_at_start: str
    author_display_name_at_start: str
    body_text_at_start: str
    published_at_start: str
    created_at: str

    @field_validator(
        "run_post_comment_id",
        "run_id",
        "run_post_id",
        "author_agent_id",
        "author_handle_at_start",
        "author_display_name_at_start",
        "body_text_at_start",
        "published_at_start",
        "created_at",
    )
    @classmethod
    def validate_text_fields(cls, value: str) -> str:
        return validate_non_empty_string(value)
