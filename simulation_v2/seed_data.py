"""Generates and loads seed data.

To run:

PYTHONPATH=. uv run python simulation_v2/seed_data.py
"""

import os

from pydantic import BaseModel

SEED_DATA_PATH = "" # {current_directory}/seed_data/{users/posts/likes/follows/etc.}.parquet

class SeedDataModel(BaseModel):
    pass


# TODO: figure out data model so I can figure out how everything should relate.
# generate 500 users
def generate_users():
    pass

def generate_posts():
    """Generate posts."""
    pass

def generate_likes():
    pass

def generate_follows():
    pass

def generate_data() -> SeedDataModel:
    return SeedDataModel()


def export_seed_data(seed_data: SeedDataModel):
    pass

if __name__ == "__main__":
    if not os.path.exists(SEED_DATA_PATH):
        seed_data: SeedDataModel = generate_data()
        export_seed_data(seed_data)
