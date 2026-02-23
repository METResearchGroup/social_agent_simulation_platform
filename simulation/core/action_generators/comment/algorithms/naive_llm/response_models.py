"""Pydantic response models for naive LLM comment prediction."""

from pydantic import BaseModel


class CommentPredictionItem(BaseModel):
    """Single comment prediction from the LLM."""

    post_id: str
    text: str


class CommentPrediction(BaseModel):
    """LLM output schema for comment prediction."""

    comments: list[CommentPredictionItem]
