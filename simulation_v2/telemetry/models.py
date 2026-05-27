"""Pydantic models for simulation v2 telemetry summaries."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

ActionType = Literal[
    "like_posts",
    "write_post",
    "follow_users",
    "comment_on_post",
]


class LatencyPercentiles(BaseModel):
    p50: float
    p90: float
    p99: float | None = None


class ActionLlmMetricsSummary(BaseModel):
    request_count: int
    total_cost_usd: float
    latency_ms: LatencyPercentiles


class TurnLlmMetricsSummary(BaseModel):
    turn_number: int
    run_id: str
    by_action: dict[ActionType, ActionLlmMetricsSummary]
    overall: ActionLlmMetricsSummary


class RunLlmMetricsSummary(BaseModel):
    run_id: str
    total_turns: int
    by_turn: list[TurnLlmMetricsSummary]
    overall: ActionLlmMetricsSummary
