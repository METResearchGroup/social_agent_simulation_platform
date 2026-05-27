"""Structured LLM output models and generation result types."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

ActionType = Literal["like_post", "write_post", "follow_user", "comment_on_post"]
GenerationStatus = Literal["completed", "failed", "schema_failed"]


class LlmLikePostOutput(BaseModel):
    post_ids: list[str] = Field(default_factory=list)


class LlmWritePostOutput(BaseModel):
    content: str


class LlmFollowUserOutput(BaseModel):
    user_ids: list[str] = Field(default_factory=list)


class LlmCommentOnPostOutput(BaseModel):
    parent_post_id: str
    content: str


class LlmGenerationResult(BaseModel):
    status: GenerationStatus
    parsed: BaseModel | None = None
    latency_ms: float | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cost_usd: float | None = None
    error: str | None = None
    raw_response_json: dict[str, Any] | None = None
