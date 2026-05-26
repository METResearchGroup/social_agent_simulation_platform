"""Runs a full run of the simulation.

To run:

PYTHONPATH=. uv run python simulation_v2/main.py

Default config: 3 users, 5 posts per user, 3 turns.
Progress bars show turn completion (run-level), feed generation, and agents per turn.
"""

from __future__ import annotations

from simulation_v2.config import LocalSimulationConfig, SeedConfig
from simulation_v2.load_seed_data import load_seed_data
from simulation_v2.logging_config import configure_simulation_logging
from simulation_v2.models.turn import TurnInputsModel
from simulation_v2.simulate_run import simulate_run

configure_simulation_logging()


def main() -> TurnInputsModel:
    config = LocalSimulationConfig.default().model_copy(
        update={"seed": SeedConfig(total_users=3, total_posts_per_user=5)}
    )
    print(
        f"Starting simulation: users={config.seed.total_users} "
        f"posts_per_user={config.seed.total_posts_per_user} "
        f"turns={config.total_turns}"
    )
    turn_inputs = TurnInputsModel(
        seed_data=load_seed_data(
            total_users=config.seed.total_users,
            total_posts_per_user=config.seed.total_posts_per_user,
        ),
        total_turns=config.total_turns,
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
