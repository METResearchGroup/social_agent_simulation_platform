"""Runs a full run of the simulation via the local control plane.

PR 4 runs are status-only stubs (no seed import or LLM calls) until PR 5+.

To run:

PYTHONPATH=. uv run python simulation_v2/main.py

Default config: 3 users, 5 posts per user, 3 turns.
"""

from __future__ import annotations

from simulation_v2.config import LocalSimulationConfig, SeedConfig
from simulation_v2.control_plane.service import get_run_summary, start_run
from simulation_v2.logging_config import configure_simulation_logging

configure_simulation_logging()


def main() -> None:
    config = LocalSimulationConfig.default().model_copy(
        update={"seed": SeedConfig(total_users=3, total_posts_per_user=5)}
    )
    print(
        f"Starting simulation: users={config.seed.total_users} "
        f"posts_per_user={config.seed.total_posts_per_user} "
        f"turns={config.total_turns}"
    )
    run_id = start_run(config, dispatch=True)
    run, turns = get_run_summary(run_id, db_path=config.storage.db_path)
    completed_count = sum(1 for turn in turns if turn.status == "completed")
    print(
        f"Run complete: run_id={run_id} status={run.status} "
        f"completed_turns={completed_count}/{len(turns)}"
    )


if __name__ == "__main__":
    main()
