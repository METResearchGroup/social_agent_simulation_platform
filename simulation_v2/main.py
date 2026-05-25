"""Runs a full run of the simulation.

To run:

PYTHONPATH=. uv run python simulation_v2/main.py
"""

from simulation_v2.load_seed_data import load_seed_data
from simulation_v2.models.seed_data import LoadedSeedDataModel


def main() -> LoadedSeedDataModel:
    return load_seed_data(total_users=100, total_posts_per_user=20)


if __name__ == "__main__":
    seed_data = main()
    print(f"Loaded {len(seed_data.users)} users and {len(seed_data.posts)} posts")
