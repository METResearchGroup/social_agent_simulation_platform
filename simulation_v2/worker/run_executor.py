"""Run-level turn loop orchestration."""

from __future__ import annotations

import sqlite3

from simulation_v2.config import LocalSimulationConfig
from simulation_v2.db.repositories import SimulationRepositories
from simulation_v2.evals.runner import run_run_evals
from simulation_v2.telemetry.opik import configure_opik
from simulation_v2.worker.turn_executor import execute_turn


def execute_run(
    run_id: str,
    config: LocalSimulationConfig,
    conn: sqlite3.Connection,
    repos: SimulationRepositories,
) -> None:
    configure_opik()
    for turn_number in range(1, config.total_turns + 1):
        execute_turn(run_id, turn_number, config, conn, repos)
    run_run_evals(run_id, config, repos, conn)
