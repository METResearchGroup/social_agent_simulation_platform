"""Pydantic row models for generated feeds."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class FeedPostView(BaseModel):
    post_id: str
    author_id: str
    content: str
    created_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class GeneratedFeedRecord(BaseModel):
    feed_id: str
    run_id: str
    turn_id: str
    user_id: str
    algorithm: str
    feed_post_ids: list[str]
    feed_posts: list[FeedPostView]
    created_at: str
