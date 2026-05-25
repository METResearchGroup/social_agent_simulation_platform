"""Runs a full run of the simulation.

To run:

PYTHONPATH=. uv run python simulation_v2/main.py
"""

from simulation_v2.load_seed_data import load_seed_data
from simulation_v2.models.turn import TurnInputsModel
from simulation_v2.simulate_run import simulate_run


def main() -> TurnInputsModel:
    turn_inputs = TurnInputsModel(
        seed_data=load_seed_data(total_users=100, total_posts_per_user=20),
        total_turns=10,
    )
    simulate_run(turn_inputs)
    return turn_inputs


if __name__ == "__main__":
    turn_inputs = main()
    print(
        f"Loaded {len(turn_inputs.seed_data.users)} users and "
        f"{len(turn_inputs.seed_data.posts)} posts"
    )
