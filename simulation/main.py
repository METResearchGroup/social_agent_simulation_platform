import sys

from db.adapters.sqlite.sqlite import initialize_database
from simulation.core.exceptions import (
    InvalidTransitionError,
    RunCreationError,
    RunNotFoundError,
    RunStatusUpdateError,
)
from simulation.core.factories import create_engine
from simulation.core.models.runs import RunConfig

# TODO: This file will be deprecated in favor of `simulation/cli/main.py` in future PR


def do_simulation_run(config: RunConfig) -> None:
    """Execute a simulation run.

    Args:
        config: Configuration for the run
    """
    engine = create_engine()

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
