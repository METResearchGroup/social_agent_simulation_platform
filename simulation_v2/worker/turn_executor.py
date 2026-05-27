"""Single-turn execution: status transitions, snapshot load, feed and action generation."""

from __future__ import annotations

import sqlite3

from simulation_v2.actions.executor import build_pending_turn_diffs
from simulation_v2.actions.service import (
    generate_and_persist_llm_actions,
    validate_and_persist_proposed_actions,
)
from simulation_v2.config import LocalSimulationConfig
from simulation_v2.db.models import TurnRecord
from simulation_v2.db.repositories import SimulationRepositories
from simulation_v2.evals.runner import run_turn_evals
from simulation_v2.feeds.service import generate_and_persist_feeds
from simulation_v2.ids import new_turn_id
from simulation_v2.telemetry.context import SimulationTraceContext
from simulation_v2.time import get_current_timestamp
from simulation_v2.worker.state import TurnStateSnapshot, load_turn_snapshot


def execute_turn(
    run_id: str,
    turn_number: int,
    _config: LocalSimulationConfig,
    conn: sqlite3.Connection,
    repos: SimulationRepositories,
) -> TurnStateSnapshot | None:
    existing = repos.get_turn_by_run_and_number(run_id, turn_number, conn)
    if existing is not None and existing.status == "completed":
        return None

    if existing is None:
        turn = TurnRecord(
            turn_id=new_turn_id(),
            run_id=run_id,
            turn_number=turn_number,
            status="pending",
            created_at=get_current_timestamp(),
        )
        repos.insert_turn(turn, conn)
        turn_id = turn.turn_id
    else:
        turn_id = existing.turn_id

    repos.update_turn_status(turn_id, "running", conn)
    snapshot = load_turn_snapshot(run_id, turn_id, repos, conn)
    feed_records = generate_and_persist_feeds(
        snapshot, snapshot.config.feed, repos, conn
    )
    trace_ctx = SimulationTraceContext(
        run_id=run_id,
        turn_number=snapshot.turn_number,
    )
    generate_and_persist_llm_actions(
        snapshot,
        feed_records,
        snapshot.config.action,
        snapshot.config.llm,
        repos,
        conn,
        trace_ctx=trace_ctx,
    )
    proposed_records = validate_and_persist_proposed_actions(
        snapshot,
        feed_records,
        snapshot.config.action,
        repos,
        conn,
    )
    validated = [r for r in proposed_records if r.record_kind == "validated"]
    diffs = build_pending_turn_diffs(validated, snapshot)
    repos.persist_turn_diffs(diffs, conn)
    repos.update_turn_status(turn_id, "completed", conn)
    run_turn_evals(
        run_id=run_id,
        turn_id=turn_id,
        turn_number=snapshot.turn_number,
        config=snapshot.config,
        repos=repos,
        conn=conn,
    )
    return snapshot
