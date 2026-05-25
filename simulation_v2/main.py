"""Runs a full run of the simulation.

To run:

PYTHONPATH=. uv run python simulation_v2/main.py

Default config: 10 users, 5 posts per user, 3 turns.
Progress bars show turn completion (run-level) and agent completion (turn-level).
"""

from __future__ import annotations

from simulation_v2.load_seed_data import load_seed_data
from simulation_v2.logging_config import configure_simulation_logging
from simulation_v2.models.turn import TurnInputsModel
from simulation_v2.simulate_run import simulate_run

configure_simulation_logging()


def main() -> TurnInputsModel:
    turn_inputs = TurnInputsModel(
        seed_data=load_seed_data(total_users=10, total_posts_per_user=5),
        total_turns=3,
    )
    run_id = simulate_run(turn_inputs, show_progress=True)
    print(
        f"Run complete: run_id={run_id} "
        f"users={len(turn_inputs.seed_data.users)} "
        f"posts={len(turn_inputs.seed_data.posts)} "
        f"turns={turn_inputs.total_turns}"
    )
    return turn_inputs


if __name__ == "__main__":
    main()
