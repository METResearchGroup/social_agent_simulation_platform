"""In-memory seed dataset models for simulation_v2."""

from __future__ import annotations

from pydantic import BaseModel, Field


class UserModel(BaseModel):
    user_id: str
    name: str
    email: str
    username: str
    created_at: str


class PostModel(BaseModel):
    post_id: str
    user_id: str
    content: str
    created_at: str


class LikeModel(BaseModel):
    like_id: str
    user_id: str
    post_id: str
    created_at: str


class FollowModel(BaseModel):
    follower_id: str
    followee_id: str


class SeedDataModel(BaseModel):
    users: list[UserModel] = Field(default_factory=list)
    posts: list[PostModel] = Field(default_factory=list)
    likes: list[LikeModel] = Field(default_factory=list)
    follows: list[FollowModel] = Field(default_factory=list)


class LoadedUserModel(BaseModel):
    user_id: str
    name: str
    email: str
    username: str
    created_at: str
    num_followers: int
    num_follows: int


class LoadedPostModel(BaseModel):
    post_id: str
    user_id: str
    content: str
    created_at: str
    num_likes: int


class LoadedSeedDataModel(BaseModel):
    users: dict[str, LoadedUserModel] = Field(default_factory=dict)
    posts: dict[str, LoadedPostModel] = Field(default_factory=dict)


class SeedDataset(BaseModel):
    users: dict[str, LoadedUserModel] = Field(default_factory=dict)
    posts: dict[str, LoadedPostModel] = Field(default_factory=dict)
    likes: dict[str, LikeModel] = Field(default_factory=dict)
    follows: dict[str, FollowModel] = Field(default_factory=dict)


class SeedImportSummary(BaseModel):
    user_count: int = Field(ge=0)
    post_count: int = Field(ge=0)
    like_count: int = Field(ge=0)
    follow_count: int = Field(ge=0)
    memory_count: int = Field(ge=0)
