"""Request/response schemas for the simulation run API."""

from enum import Enum

from pydantic import BaseModel, field_validator, model_validator

from simulation.core.models.runs import RunStatus
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


class RunResponseStatus(str, Enum):
    """Status of a simulation run as returned by the API."""

    COMPLETED = "completed"
    FAILED = "failed"


class RunResponse(BaseModel):
    """Response body for POST /v1/simulations/run."""

    run_id: str
    status: RunResponseStatus
    num_agents: int
    num_turns: int
    likes_per_turn: list[LikesPerTurnItem]
    total_likes: int
    error: ErrorDetail | None = None

    @model_validator(mode="after")
    def _validate_status_error_consistency(self) -> "RunResponse":
        if self.status == RunResponseStatus.FAILED and self.error is None:
            raise ValueError("error must be set when status is 'failed'")
        if self.status == RunResponseStatus.COMPLETED and self.error is not None:
            raise ValueError("error must be None when status is 'completed'")
        return self


class RunConfigDetail(BaseModel):
    """Configuration for a persisted run."""

    num_agents: int
    num_turns: int
    feed_algorithm: str


class TurnActionsItem(BaseModel):
    """One turn summary with aggregate action counts."""

    turn_number: int
    created_at: str
    total_actions: dict[str, int]


class RunDetailsResponse(BaseModel):
    """Response body for GET /v1/simulations/runs/{run_id}."""

    run_id: str
    status: RunStatus
    created_at: str
    started_at: str
    completed_at: str | None = None
    config: RunConfigDetail
    turns: list[TurnActionsItem]
