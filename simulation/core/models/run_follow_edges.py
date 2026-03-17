"""Immutable run-start snapshot of an internal follow edge.

Exists to answer the question "what follow graph did these selected agents
start with in this run?"

Usage pattern: It is write-once at run init (transactionally with run-agent
snapshots), then read-only. It is a historical/frozen view, intentionally
decoupled from mutable agent_follow_edges

Represents one directed edge (follower -> target) in the selected agents'
follow graph at the moment a run starts. Rows are persisted in
`run_follow_edges` and treated as historical state for that run; they do not
track later changes to `agent_follow_edges`.

Invariants:
- `run_id` scopes the snapshot to a single run.
- `follower_agent_id` and `target_agent_id` must both belong to run membership.
- `follower_agent_id != target_agent_id`.
- `created_at` is the run creation timestamp (snapshot timestamp), not edge-mutation time.
"""

from pydantic import BaseModel, ConfigDict, field_validator

from lib.validation_utils import validate_non_empty_string


class RunFollowEdgeSnapshot(BaseModel):
    """Frozen run-start follow relationship anchored to run membership."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    follower_agent_id: str
    target_agent_id: str
    created_at: str

    @field_validator(
        "run_id",
        "follower_agent_id",
        "target_agent_id",
        "created_at",
    )
    @classmethod
    def validate_text_fields(cls, value: str) -> str:
        return validate_non_empty_string(value)
