"""In-memory seed dataset models for simulation_v2."""

from __future__ import annotations

from pydantic import BaseModel, Field

from simulation_v2.models.seed_data import (
    FollowModel,
    LikeModel,
    LoadedPostModel,
    LoadedUserModel,
)


class SeedDataset(BaseModel):
    users: dict[str, LoadedUserModel] = Field(default_factory=dict)
    posts: dict[str, LoadedPostModel] = Field(default_factory=dict)
    likes: dict[str, LikeModel] = Field(default_factory=dict)
    follows: dict[str, FollowModel] = Field(default_factory=dict)


class SeedImportSummary(BaseModel):
    user_count: int
    post_count: int
    like_count: int
    follow_count: int
    memory_count: int
