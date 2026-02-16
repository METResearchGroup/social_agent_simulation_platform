"""Request/response schemas for the simulation run API."""

from pydantic import BaseModel, field_validator

from simulation.core.validators import (
    validate_feed_algorithm,
    validate_num_agents,
    validate_num_turns,
)


class RunRequest(BaseModel):
    """Request body for POST /v1/simulations/run."""

    num_agents: int
    num_turns: int | None = None
    feed_algorithm: str | None = None

    @field_validator("num_agents")
    @classmethod
    def _validate_num_agents(cls, v: int) -> int:
        return validate_num_agents(v)

    @field_validator("num_turns")
    @classmethod
    def _validate_num_turns(cls, v: int | None) -> int | None:
        return validate_num_turns(v)

    @field_validator("feed_algorithm")
    @classmethod
    def _validate_feed_algorithm(cls, v: str | None) -> str | None:
        return validate_feed_algorithm(v)


class LikesPerTurnItem(BaseModel):
    """One entry in the likes-per-turn list."""

    turn_number: int
    likes: int


class ErrorDetail(BaseModel):
    """Error payload included when status is failed or on server error."""

    code: str
    message: str
    detail: str | None = None


class RunResponse(BaseModel):
    """Response body for POST /v1/simulations/run."""

    run_id: str
    status: str  # "completed" | "failed"
    num_agents: int
    num_turns: int
    likes_per_turn: list[LikesPerTurnItem]
    total_likes: int
    error: ErrorDetail | None = None
