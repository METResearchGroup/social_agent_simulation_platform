"""Pydantic response models for naive LLM like prediction."""

from pydantic import BaseModel, Field


class LikePrediction(BaseModel):
    """LLM output schema for like prediction."""

    post_ids: list[str] = Field(description="Post IDs the user would like")
