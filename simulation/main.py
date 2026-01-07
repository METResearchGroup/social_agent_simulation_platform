import sys

from db.db import initialize_database
from db.exceptions import (
    InvalidTransitionError,
    RunCreationError,
    RunNotFoundError,
    RunStatusUpdateError,
)
from db.repositories.feed_post_repository import create_sqlite_feed_post_repository
from db.repositories.generated_bio_repository import (
    create_sqlite_generated_bio_repository,
)
from db.repositories.generated_feed_repository import (
    create_sqlite_generated_feed_repository,
)
from db.repositories.profile_repository import create_sqlite_profile_repository
from db.repositories.run_repository import create_sqlite_repository
from simulation.core.engine import SimulationEngine
from simulation.core.models.runs import RunConfig

# TODO: This file will be deprecated in favor of `simulation/cli/main.py` in future PR


def create_engine_inline() -> SimulationEngine:
    """Create a SimulationEngine with SQLite repositories.

    This is a temporary inline factory function. It will be replaced with
    a proper factory from `simulation.core.dependencies` in PR 8.

    Returns:
        SimulationEngine configured with SQLite repositories.
    """
    return SimulationEngine(
        run_repo=create_sqlite_repository(),
        profile_repo=create_sqlite_profile_repository(),
        feed_post_repo=create_sqlite_feed_post_repository(),
        generated_bio_repo=create_sqlite_generated_bio_repository(),
        generated_feed_repo=create_sqlite_generated_feed_repository(),
    )


def do_simulation_run(config: RunConfig) -> None:
    """Execute a simulation run.

    Args:
        config: Configuration for the run
    """
    engine = create_engine_inline()

    print(f"Starting simulation: {config.num_agents} agents, {config.num_turns} turns")

    try:
        run = engine.execute_run(config)
        print(f"Simulation run {run.run_id} completed in {run.total_turns} turns.")
    except Exception as e:
        # Error handling matches previous implementation
        # Engine handles status updates internally, but we still catch and print
        print(f"Error: Failed to complete simulation: {e}")
        raise


def main():
    """CLI entry point - creates repository and runs simulation."""
    initialize_database()

    config = RunConfig(
        num_agents=10,
        num_turns=10,
        feed_algorithm="chronological",
    )

    try:
        do_simulation_run(config)
    except (
        RunNotFoundError,
        InvalidTransitionError,
        RunCreationError,
        RunStatusUpdateError,
        RuntimeError,
    ) as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
