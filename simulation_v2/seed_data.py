"""Generates and loads seed data (legacy entry point).

To run:

PYTHONPATH=. uv run python simulation_v2/seed_data.py
"""

from __future__ import annotations

from simulation_v2.seed.generator import (
    SEED_DATA_PATH,
    export_seed_data,
    generate_data,
    load_seed_data_from_parquet,
    print_seed_data_statistics,
    seed_data_dir_exists,
)

__all__ = [
    "SEED_DATA_PATH",
    "export_seed_data",
    "generate_data",
    "load_seed_data_from_parquet",
    "print_seed_data_statistics",
    "seed_data_dir_exists",
]

if __name__ == "__main__":
    if not seed_data_dir_exists():
        seed_data = generate_data()
        export_seed_data(seed_data)
        print_seed_data_statistics(seed_data)
