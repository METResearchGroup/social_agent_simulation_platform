"""Pydantic row models for eval runs and metrics."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

EvalScope = Literal["turn", "run"]


class EvalRunRecord(BaseModel):
    eval_run_id: str
    run_id: str
    turn_id: str | None = None
    scope: EvalScope
    plugin_name: str
    status: str
    created_at: str
    finished_at: str | None = None
    error: str | None = None


class EvalMetricRecord(BaseModel):
    eval_metric_id: str
    eval_run_id: str
    run_id: str
    turn_id: str | None = None
    plugin_name: str
    metric_name: str
    metric_value: float
    metadata_json: dict[str, Any] | None = None
    created_at: str
