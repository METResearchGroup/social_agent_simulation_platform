from __future__ import annotations

import uuid

from pydantic import BaseModel, field_validator

from lib.validation_utils import validate_non_empty_string, validate_nonnegative_value


class GeneratedFeed(BaseModel):
    """A feed generated for an AI agent."""

    feed_id: str
    run_id: str
    turn_number: int
    agent_handle: str
    post_ids: list[str]
    created_at: str

    @field_validator("feed_id", "run_id", "agent_handle", "created_at", mode="before")
    @classmethod
    def validate_required_strings(cls, v: object) -> str:
        return validate_non_empty_string(v)  # pyright: ignore[reportArgumentType]

    @field_validator("turn_number", mode="before")
    @classmethod
    def validate_turn_number(cls, v: int) -> int:
        """Validate that turn_number is a non-negative integer."""
        return int(validate_nonnegative_value(v, "turn_number"))

    @field_validator("post_ids", mode="before")
    @classmethod
    def validate_post_ids(cls, v: object) -> list[str]:
        """Validate and normalize post_ids by stripping and rejecting empty entries."""
        if v is None:
            raise ValueError("post_ids cannot be None")
        if not isinstance(v, list):
            raise ValueError("post_ids must be a list")

        normalized: list[str] = []
        for post_id in v:
            if post_id is None:
                raise ValueError("post_ids contains null entry")
            if not isinstance(post_id, str):
                raise ValueError("post_ids contains non-string entry")
            cleaned = post_id.strip()
            if cleaned == "":
                raise ValueError("post_ids contains empty/whitespace-only entry")
            normalized.append(cleaned)
        return normalized

    @classmethod
    def generate_feed_id(cls) -> str:
        return f"feed_{uuid.uuid4()}"
