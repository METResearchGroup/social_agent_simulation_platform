"""Eval plugin contracts for simulation_v2."""

from __future__ import annotations

import sqlite3
from typing import ClassVar, Literal, Protocol

from pydantic import BaseModel, Field

from simulation_v2.config import LocalSimulationConfig
from simulation_v2.db.models.evals import EvalScope
from simulation_v2.db.repositories import SimulationRepositories


class EvalMetricDraft(BaseModel):
    metric_name: str
    metric_value: float
    metadata_json: dict | None = None


class EvalResult(BaseModel):
    plugin_name: str
    status: Literal["passed", "failed"]
    metrics: list[EvalMetricDraft]
    warnings: list[str] = Field(default_factory=list)


class EvalContext(BaseModel):
    repos: SimulationRepositories
    conn: sqlite3.Connection
    run_id: str
    config: LocalSimulationConfig
    scope: EvalScope
    turn_id: str | None
    turn_number: int | None
    turn_summary: dict | None = None

    model_config = {"arbitrary_types_allowed": True}


class EvalPlugin(Protocol):
    name: ClassVar[str]
    scope: ClassVar[EvalScope]

    def run(self, context: EvalContext) -> EvalResult: ...
