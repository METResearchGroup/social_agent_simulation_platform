"""Pydantic row models for agent memory."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

MemoryType = Literal["episodic", "personalized", "social"]


class AgentMemoryRecord(BaseModel):
    run_id: str
    user_id: str
    preferences_json: dict[str, Any] | None = None
    episodic: str | None = None
    personalized: str | None = None
    social: str | None = None
    updated_at: str


class MemoryDiffRecord(BaseModel):
    memory_diff_id: str
    run_id: str
    turn_id: str
    user_id: str
    memory_type: MemoryType
    content: str
    created_at: str
