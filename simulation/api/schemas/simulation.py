"""Request/response schemas for the simulation run API."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, field_validator, model_validator

from feeds.algorithms.interfaces import FeedAlgorithmMetadata
from simulation.core.models.actions import TurnAction
from simulation.core.models.metrics import ComputedMetrics
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


class FeedAlgorithmSchema(FeedAlgorithmMetadata):
    """API response for GET /v1/simulations/feed-algorithms."""

    id: str  # algorithm_id from registry


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
    created_at: str
    status: RunResponseStatus
    num_agents: int
    num_turns: int
    turns: list[TurnSummaryItem]
    run_metrics: ComputedMetrics | None = None
    error: ErrorDetail | None = None

    @model_validator(mode="after")
    def _validate_status_error_consistency(self) -> "RunResponse":
        if self.status == RunResponseStatus.FAILED and self.error is None:
            raise ValueError("error must be set when status is 'failed'")
        if self.status == RunResponseStatus.COMPLETED and self.error is not None:
            raise ValueError("error must be None when status is 'completed'")
        return self


class DefaultConfigSchema(BaseModel):
    """Default config for simulation start form."""

    num_agents: int
    num_turns: int


class RunConfigDetail(BaseModel):
    """Configuration for a persisted run."""

    num_agents: int
    num_turns: int
    feed_algorithm: str


class RunListItem(BaseModel):
    """Summary item for listing simulation runs."""

    run_id: str
    created_at: str
    total_turns: int
    total_agents: int
    status: RunStatus


class CreateAgentRequest(BaseModel):
    """Request body for POST /v1/simulations/agents.

    Fast-follows (not yet supported):
    - comments: list of {text, postUri}
    - likedPostUris: list of post URIs
    - linkedAgentHandles: list of agent handles to link
    """

    handle: str
    display_name: str
    bio: str = ""

    @field_validator("handle")
    @classmethod
    def _validate_handle(cls, v: str) -> str:
        from lib.validation_utils import validate_non_empty_string

        return validate_non_empty_string(v.strip(), "handle")

    @field_validator("display_name")
    @classmethod
    def _validate_display_name(cls, v: str) -> str:
        from lib.validation_utils import validate_non_empty_string

        return validate_non_empty_string(v.strip(), "display_name")


class AgentSchema(BaseModel):
    """Agent profile for the simulation UI."""

    handle: str
    name: str
    bio: str
    generated_bio: str
    followers: int
    following: int
    posts_count: int


class FeedSchema(BaseModel):
    """Feed metadata for one agent in a turn."""

    feed_id: str
    run_id: str
    turn_number: int
    agent_handle: str
    post_uris: list[str]
    created_at: str


class PostSchema(BaseModel):
    """Post content for display in agent feeds. Matches ApiPost in ui/lib/api/simulation.ts."""

    uri: str
    author_display_name: str
    author_handle: str
    text: str
    bookmark_count: int
    like_count: int
    quote_count: int
    reply_count: int
    repost_count: int
    created_at: str


class AgentActionSchema(BaseModel):
    """Action event performed by an agent in a turn."""

    action_id: str
    agent_handle: str
    post_uri: str | None = None
    user_id: str | None = None
    type: TurnAction
    created_at: str


class TurnSchema(BaseModel):
    """Full turn payload consumed by the UI."""

    turn_number: int
    agent_feeds: dict[str, FeedSchema]
    agent_actions: dict[str, list[AgentActionSchema]]


class TurnActionsItem(BaseModel):
    """One turn summary with aggregate action counts."""

    turn_number: int
    created_at: str
    total_actions: dict[str, int]
    metrics: ComputedMetrics | None = None


class RunDetailsResponse(BaseModel):
    """Response body for GET /v1/simulations/runs/{run_id}."""

    run_id: str
    status: RunStatus
    created_at: str
    started_at: str
    completed_at: str | None = None
    config: RunConfigDetail
    turns: list[TurnActionsItem]
    run_metrics: ComputedMetrics | None = None


class TurnSummaryItem(BaseModel):
    """One turn summary with computed metrics."""

    turn_number: int
    created_at: str
    total_actions: dict[str, int]
    metrics: ComputedMetrics
