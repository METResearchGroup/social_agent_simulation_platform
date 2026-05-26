"""Pydantic row models for runs and turns."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

RunStatus = Literal["queued", "running", "completed", "failed"]
TurnStatus = Literal["pending", "running", "completed", "failed"]


class RunRecord(BaseModel):
    run_id: str
    status: RunStatus
    config_json: dict[str, Any]
    seed_metadata_json: dict[str, Any] | None = None
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None


class TurnRecord(BaseModel):
    turn_id: str
    run_id: str
    turn_number: int
    status: TurnStatus
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None
