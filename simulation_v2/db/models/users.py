"""Pydantic row models for seed/social entities."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class UserRecord(BaseModel):
    user_id: str
    run_id: str
    name: str
    email: str
    username: str
    profile_json: dict[str, Any] | None = None
    created_at: str


class PostRecord(BaseModel):
    post_id: str
    run_id: str
    author_id: str
    content: str
    created_at: str
    created_at_turn: int
    metadata_json: dict[str, Any] | None = None


class LikeRecord(BaseModel):
    like_id: str
    run_id: str
    post_id: str
    author_id: str
    created_at: str
    created_at_turn: int
    metadata_json: dict[str, Any] | None = None


class FollowRecord(BaseModel):
    follow_id: str
    run_id: str
    follower_id: str
    followee_id: str
    created_at: str
    created_at_turn: int
    metadata_json: dict[str, Any] | None = None


class CommentRecord(BaseModel):
    comment_id: str
    run_id: str
    parent_post_id: str
    author_id: str
    content: str
    created_at: str
    created_at_turn: int
    metadata_json: dict[str, Any] | None = None
