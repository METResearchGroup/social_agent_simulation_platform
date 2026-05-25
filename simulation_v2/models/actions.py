from __future__ import annotations

from pydantic import BaseModel, Field

from simulation_v2.models.seed_data import FollowModel, LikeModel, PostModel


class LlmLikePostsOutput(BaseModel):
    """Structured LLM output selecting posts to like by ID."""

    post_ids: list[str] = Field(default_factory=list)


class LlmWritePostOutput(BaseModel):
    """Structured LLM output for a new post body."""

    content: str


class LlmFollowUsersOutput(BaseModel):
    """Structured LLM output selecting users to follow by ID."""

    user_ids: list[str] = Field(default_factory=list)


class AgentTurnActions(BaseModel):
    """Resolved action records produced for one user in a turn."""

    likes: list[LikeModel] = Field(default_factory=list)
    posts: list[PostModel] = Field(default_factory=list)
    follows: list[FollowModel] = Field(default_factory=list)


class AllAgentsTurnActions(BaseModel):
    """Aggregated action records for all users in a turn."""

    actions_by_user_id: dict[str, AgentTurnActions] = Field(default_factory=dict)
