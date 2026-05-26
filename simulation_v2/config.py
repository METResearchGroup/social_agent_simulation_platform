"""Typed local simulation configuration models."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class StorageConfig(BaseModel):
    db_path: Path = Path("simulation_v2/local_simulation.sqlite3")


class SeedConfig(BaseModel):
    total_users: int = 10
    total_posts_per_user: int = 5

    @field_validator("total_users")
    @classmethod
    def validate_total_users(cls, value: int) -> int:
        if value < 1:
            raise ValueError("total_users must be >= 1")
        return value

    @field_validator("total_posts_per_user")
    @classmethod
    def validate_total_posts_per_user(cls, value: int) -> int:
        if value < 1:
            raise ValueError("total_posts_per_user must be >= 1")
        return value


class FeedConfig(BaseModel):
    algorithm: Literal["most_liked", "reverse_chronological"] = "most_liked"
    max_posts: int = 25
    include_probability: float = 0.5

    @field_validator("include_probability")
    @classmethod
    def validate_include_probability(cls, value: float) -> float:
        if not 0 <= value <= 1:
            raise ValueError("include_probability must be between 0 and 1")
        return value


class ActionConfig(BaseModel):
    enable_like_post: bool = True
    enable_write_post: bool = True
    enable_follow_user: bool = True
    enable_comment_on_post: bool = True
    max_likes_per_turn: int = 10
    max_posts_per_turn: int = 5
    max_follows_per_turn: int = 5
    max_comments_per_turn: int = 5

    @field_validator(
        "max_likes_per_turn",
        "max_posts_per_turn",
        "max_follows_per_turn",
        "max_comments_per_turn",
    )
    @classmethod
    def validate_max_per_turn(cls, value: int) -> int:
        if value < 0:
            raise ValueError("max_*_per_turn must be >= 0")
        return value


class LlmConfig(BaseModel):
    model: str = "gpt-5-nano"
    temperature: float = 0.7


class EvalConfig(BaseModel):
    enabled: bool = True
    fail_run_on_error: bool = False
    turn_plugins: list[str] = Field(
        default_factory=lambda: [
            "action_counts",
            "invalid_action_rate",
            "feed_coverage",
            "llm_structured_output",
        ]
    )
    run_plugins: list[str] = Field(
        default_factory=lambda: [
            "action_counts",
            "invalid_action_rate",
            "feed_coverage",
            "llm_structured_output",
        ]
    )


class LocalSimulationConfig(BaseModel):
    total_turns: int = 3
    seed: SeedConfig = Field(default_factory=SeedConfig)
    feed: FeedConfig = Field(default_factory=FeedConfig)
    action: ActionConfig = Field(default_factory=ActionConfig)
    llm: LlmConfig = Field(default_factory=LlmConfig)
    evals: EvalConfig = Field(default_factory=EvalConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)

    @field_validator("total_turns")
    @classmethod
    def validate_total_turns(cls, value: int) -> int:
        if value < 1:
            raise ValueError("total_turns must be >= 1")
        return value

    @classmethod
    def default(cls) -> LocalSimulationConfig:
        return cls()
