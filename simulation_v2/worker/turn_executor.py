"""Single-turn execution: status transitions, snapshot load, stub body."""

from __future__ import annotations

import sqlite3

from simulation_v2.config import LocalSimulationConfig
from simulation_v2.db.models import TurnRecord
from simulation_v2.db.repositories import SimulationRepositories
from simulation_v2.ids import new_turn_id
from simulation_v2.time import get_current_timestamp
from simulation_v2.worker.state import TurnStateSnapshot, load_turn_snapshot


def _execute_turn_stub(_snapshot: TurnStateSnapshot) -> None:
    """Placeholder for PR 7+ turn execution (feeds, actions, memory).

    Snapshot loading is wired in PR 6; feed generation and LLM actions follow in PR 7+.
    """
    pass


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
    _execute_turn_stub(snapshot)
    repos.update_turn_status(turn_id, "completed", conn)
    return snapshot
