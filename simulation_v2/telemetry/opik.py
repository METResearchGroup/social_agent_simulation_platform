"""Opik client helpers for simulation v2 telemetry."""

from __future__ import annotations

import logging
import os

import opik
from opik.integrations.langchain import OpikTracer

from lib.load_env_vars import EnvVarsContainer
from simulation_v2.models.telemetry import (
    ActionType,
    RunLlmMetricsSummary,
    TurnLlmMetricsSummary,
)
from simulation_v2.telemetry.context import SimulationTraceContext

LOGGER = logging.getLogger(__name__)

PROJECT_NAME = "simulation_engine_v2"

_configured = False
_enabled = True


def is_opik_enabled() -> bool:
    return _enabled


def configure_opik() -> None:
    """Configure Opik once. Respects ``OPIK_DISABLED=1``."""
    global _configured, _enabled

    if os.getenv("OPIK_DISABLED") == "1":
        _enabled = False
        opik.set_tracing_active(False)
        _configured = True
        return

    opik.set_tracing_active(True)

    if _configured:
        return

    try:
        workspace = EnvVarsContainer.get_env_var("OPIK_WORKSPACE")
        configure_kwargs: dict[str, object] = {
            "project_name": PROJECT_NAME,
            "automatic_approvals": True,
        }
        if workspace:
            configure_kwargs["workspace"] = workspace
        opik.configure(**configure_kwargs)  # type: ignore[arg-type]
        _enabled = True
    except Exception:
        LOGGER.warning("Failed to configure Opik; telemetry disabled", exc_info=True)
        _enabled = False
    finally:
        _configured = True


def get_opik_tracer(
    *,
    trace_ctx: SimulationTraceContext,
    action_type: ActionType,
    user_id: str,
    write_attempt_index: int | None = None,
) -> OpikTracer:
    """Build an OpikTracer for a single LLM generation."""
    metadata: dict[str, object] = {
        "turn_number": trace_ctx.turn_number,
        "action_type": action_type,
        "user_id": user_id,
        "run_id": trace_ctx.run_id,
    }
    if write_attempt_index is not None:
        metadata["write_attempt_index"] = write_attempt_index

    return OpikTracer(
        project_name=PROJECT_NAME,
        thread_id=trace_ctx.run_id,
        metadata=metadata,
    )


def log_turn_llm_summary_to_opik(summary: TurnLlmMetricsSummary) -> None:
    if not _enabled:
        return
    try:
        client = opik.Opik()
        trace = client.trace(
            name="turn_metrics_summary",
            tags=["metrics_summary", "turn"],
            thread_id=summary.run_id,
            project_name=PROJECT_NAME,
            metadata={"turn_number": summary.turn_number, "run_id": summary.run_id},
            output=summary.model_dump(),
        )
        trace.end()
    except Exception:
        LOGGER.warning("Failed to log turn LLM summary to Opik", exc_info=True)


def log_run_llm_summary_to_opik(summary: RunLlmMetricsSummary) -> None:
    if not _enabled:
        return
    try:
        client = opik.Opik()
        trace = client.trace(
            name="run_metrics_summary",
            tags=["metrics_summary", "run"],
            thread_id=summary.run_id,
            project_name=PROJECT_NAME,
            metadata={"run_id": summary.run_id, "total_turns": summary.total_turns},
            output=summary.model_dump(),
        )
        trace.end()
    except Exception:
        LOGGER.warning("Failed to log run LLM summary to Opik", exc_info=True)


def flush_opik() -> None:
    if not _enabled:
        return
    try:
        opik.Opik().flush()
        opik.flush_tracker()
    except Exception:
        LOGGER.warning("Failed to flush Opik telemetry", exc_info=True)
