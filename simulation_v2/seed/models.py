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
class SeedImportSummary(BaseModel):
    user_count: int = Field(ge=0)
    post_count: int = Field(ge=0)
    like_count: int = Field(ge=0)
    follow_count: int = Field(ge=0)
    memory_count: int = Field(ge=0)
