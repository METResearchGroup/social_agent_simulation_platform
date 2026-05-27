"""Runs a full run of the simulation via the local control plane.

Seed users, posts, likes, follows, and agent memories are persisted to SQLite
before the turn loop. Each turn loads a snapshot, generates feeds, and runs LLM
action generation (requires ``OPENAI_API_KEY`` with default action config).

To run:

PYTHONPATH=. uv run python simulation_v2/main.py

Default config: 3 users, 5 posts per user, 3 turns.
"""

from __future__ import annotations

import sys
from pathlib import Path

# TODO: remove at end of project when promoting project as completed.
# Running as `python simulation_v2/main.py` puts this package dir on sys.path[0],
# which shadows repo-root `lib/` (e.g. load_env_vars). Prefer repo root for imports.
_script_dir = Path(__file__).resolve().parent
if sys.path and Path(sys.path[0]).resolve() == _script_dir:
    del sys.path[0]

# ruff: noqa: E402
from simulation_v2.config import LocalSimulationConfig, SeedConfig
from simulation_v2.control_plane.service import get_run_summary, start_run
from simulation_v2.db.connection import transaction
from simulation_v2.db.database import SimulationDatabase
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
    db = SimulationDatabase(config.storage.db_path)
    with transaction(config.storage.db_path) as conn:
        counts = db.repos.count_seed_entities_for_run(run_id, conn)
    print(
        f"Run complete: run_id={run_id} status={run.status} "
        f"completed_turns={completed_count}/{len(turns)} "
        f"users={counts['user_count']} posts={counts['post_count']}"
    )


if __name__ == "__main__":
    main()
