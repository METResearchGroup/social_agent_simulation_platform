"""Execute configured eval plugins and persist eval run/metric rows."""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass

from simulation_v2.config import LocalSimulationConfig
from simulation_v2.db.models.evals import EvalMetricRecord, EvalRunRecord, EvalScope
from simulation_v2.db.repositories import SimulationRepositories
from simulation_v2.evals.interfaces import EvalContext, EvalResult
from simulation_v2.evals.registry import get_eval_plugin
from simulation_v2.ids import new_eval_metric_id, new_eval_run_id
from simulation_v2.time import get_current_timestamp

logger = logging.getLogger(__name__)

_FAILED_STATUS_MESSAGE = "eval plugin returned failed status"


class EvalExecutionError(Exception):
    """Raised when eval execution fails and fail_run_on_error is enabled."""


@dataclass(frozen=True)
class EvalPluginRunSummary:
    eval_run_id: str
    plugin_name: str
    status: str
    metrics: list[EvalMetricRecord]


def run_turn_evals(
    run_id: str,
    turn_id: str,
    turn_number: int,
    config: LocalSimulationConfig,
    repos: SimulationRepositories,
    conn: sqlite3.Connection,
) -> list[EvalPluginRunSummary]:
    if not config.evals.enabled:
        return []
    return _run_evals(
        run_id=run_id,
        config=config,
        repos=repos,
        conn=conn,
        scope="turn",
        turn_id=turn_id,
        turn_number=turn_number,
        plugin_names=config.evals.turn_plugins,
    )


def run_run_evals(
    run_id: str,
    config: LocalSimulationConfig,
    repos: SimulationRepositories,
    conn: sqlite3.Connection,
) -> list[EvalPluginRunSummary]:
    if not config.evals.enabled:
        return []
    return _run_evals(
        run_id=run_id,
        config=config,
        repos=repos,
        conn=conn,
        scope="run",
        turn_id=None,
        turn_number=None,
        plugin_names=config.evals.run_plugins,
    )


def _run_evals(
    *,
    run_id: str,
    config: LocalSimulationConfig,
    repos: SimulationRepositories,
    conn: sqlite3.Connection,
    scope: EvalScope,
    turn_id: str | None,
    turn_number: int | None,
    plugin_names: list[str],
) -> list[EvalPluginRunSummary]:
    summaries: list[EvalPluginRunSummary] = []
    for plugin_name in plugin_names:
        plugin = get_eval_plugin(plugin_name)
        if plugin is None:
            logger.warning("unknown eval plugin %r", plugin_name)
            continue
        if plugin.scope != scope:
            logger.warning(
                "eval plugin %r has scope %r but invoked for scope %r; skipping",
                plugin_name,
                plugin.scope,
                scope,
            )
            continue

        context = EvalContext(
            repos=repos,
            conn=conn,
            run_id=run_id,
            config=config,
            scope=scope,
            turn_id=turn_id,
            turn_number=turn_number,
        )
        summary = _execute_plugin(
            plugin_name=plugin.name,
            scope=scope,
            run_id=run_id,
            turn_id=turn_id,
            context=context,
            repos=repos,
            conn=conn,
            plugin_run=plugin.run,
        )
        summaries.append(summary)
        if summary.status == "failed" and config.evals.fail_run_on_error:
            raise EvalExecutionError(
                f"eval plugin {plugin_name!r} failed with status {summary.status!r}"
            )
    return summaries


def _execute_plugin(
    *,
    plugin_name: str,
    scope: EvalScope,
    run_id: str,
    turn_id: str | None,
    context: EvalContext,
    repos: SimulationRepositories,
    conn: sqlite3.Connection,
    plugin_run,
) -> EvalPluginRunSummary:
    finished_at = get_current_timestamp()
    eval_run_id = new_eval_run_id()

    try:
        result = plugin_run(context)
    except Exception as exc:
        logger.exception("eval plugin %r raised during execution", plugin_name)
        eval_run = EvalRunRecord(
            eval_run_id=eval_run_id,
            run_id=run_id,
            turn_id=turn_id,
            scope=scope,
            plugin_name=plugin_name,
            status="failed",
            created_at=finished_at,
            finished_at=finished_at,
            error=str(exc),
        )
        repos.insert_eval_run(eval_run, conn)
        return EvalPluginRunSummary(
            eval_run_id=eval_run_id,
            plugin_name=plugin_name,
            status="failed",
            metrics=[],
        )

    status, error = _map_result_status(result)
    eval_run = EvalRunRecord(
        eval_run_id=eval_run_id,
        run_id=run_id,
        turn_id=turn_id,
        scope=scope,
        plugin_name=plugin_name,
        status=status,
        created_at=finished_at,
        finished_at=finished_at,
        error=error,
    )
    repos.insert_eval_run(eval_run, conn)
    metric_records = _persist_metrics(
        result=result,
        eval_run_id=eval_run_id,
        run_id=run_id,
        turn_id=turn_id,
        repos=repos,
        conn=conn,
    )
    logger.info(
        "eval plugin %r finished with status %r (%d metrics)",
        plugin_name,
        status,
        len(metric_records),
    )
    return EvalPluginRunSummary(
        eval_run_id=eval_run_id,
        plugin_name=plugin_name,
        status=status,
        metrics=metric_records,
    )


def _map_result_status(result: EvalResult) -> tuple[str, str | None]:
    if result.status == "passed":
        return "completed", None
    if result.warnings:
        return "failed", "; ".join(result.warnings)
    return "failed", _FAILED_STATUS_MESSAGE


def _persist_metrics(
    *,
    result: EvalResult,
    eval_run_id: str,
    run_id: str,
    turn_id: str | None,
    repos: SimulationRepositories,
    conn: sqlite3.Connection,
) -> list[EvalMetricRecord]:
    created_at = get_current_timestamp()
    metric_records: list[EvalMetricRecord] = []
    for draft in result.metrics:
        record = EvalMetricRecord(
            eval_metric_id=new_eval_metric_id(),
            eval_run_id=eval_run_id,
            run_id=run_id,
            turn_id=turn_id,
            plugin_name=result.plugin_name,
            metric_name=draft.metric_name,
            metric_value=draft.metric_value,
            metadata_json=draft.metadata_json,
            created_at=created_at,
        )
        repos.insert_eval_metric(record, conn)
        metric_records.append(record)
    return metric_records
