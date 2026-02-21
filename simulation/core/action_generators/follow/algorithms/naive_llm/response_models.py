"""Pydantic response models for naive LLM follow prediction."""

from pydantic import BaseModel, Field


class FollowPrediction(BaseModel):
    """LLM output schema for follow prediction."""

    user_ids: list[str] = Field(description="User handles to follow")
