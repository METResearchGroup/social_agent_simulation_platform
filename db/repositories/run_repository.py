"""Abstraction for repositories."""

import uuid
from abc import ABC, abstractmethod
from typing import Callable, Optional

from db.adapters.base import RunDatabaseAdapter
from db.exceptions import (
    InvalidTransitionError,
    RunCreationError,
    RunNotFoundError,
    RunStatusUpdateError,
)
from simulation.core.models.runs import Run, RunConfig, RunStatus
from simulation.core.models.turns import TurnMetadata
from simulation.core.validators import (
    validate_run_exists,
    validate_run_id,
    validate_run_status_transition,
    validate_turn_number,
    validate_turn_number_less_than_max_turns,
)


class RunRepository(ABC):
    """Abstract base class defining the interface for run repositories."""

    @abstractmethod
    def create_run(self, config: RunConfig) -> Run:
        """Create a new run."""
        raise NotImplementedError

    @abstractmethod
    def get_run(self, run_id: str) -> Optional[Run]:
        """Get a run by ID."""
        raise NotImplementedError

    @abstractmethod
    def list_runs(self) -> list[Run]:
        """List all runs."""
        raise NotImplementedError

    @abstractmethod
    def update_run_status(self, run_id: str, status: RunStatus) -> None:
        """Update a run's status.

        Raises:
            RunNotFoundError: If the run with the given ID does not exist
            InvalidTransitionError: If the status transition is invalid
            RunStatusUpdateError: If the status update fails due to a database error
        """
        raise NotImplementedError

    @abstractmethod
    def get_turn_metadata(
        self, run_id: str, turn_number: int
    ) -> Optional[TurnMetadata]:
        """Get turn metadata for a specific run and turn.

        Args:
            run_id: The ID of the run
            turn_number: The turn number (0-indexed)

        Returns:
            TurnMetadata if found, None otherwise

        Raises:
            ValueError: If run_id is empty or turn_number is negative
        """
        raise NotImplementedError

    @abstractmethod
    def write_turn_metadata(self, turn_metadata: TurnMetadata) -> None:
        """Write turn metadata to the database.

        Args:
            turn_metadata: TurnMetadata model to write

        Raises:
            ValueError: If turn_metadata is invalid
            DuplicateTurnMetadataError: If turn metadata already exists
            Exception: Database-specific exception if constraints are violated or
                      the operation fails. Implementations should document the
                      specific exception types they raise.
        """
        raise NotImplementedError


class SQLiteRunRepository(RunRepository):
    """SQLite implementation of RunRepository.

    Uses dependency injection to accept a database adapter and timestamp function,
    decoupling it from concrete implementations.
    """

    # Valid state transitions for run status
    VALID_TRANSITIONS = {
        RunStatus.RUNNING: {RunStatus.COMPLETED, RunStatus.FAILED},
        RunStatus.COMPLETED: set(),  # Terminal state
        RunStatus.FAILED: set(),  # Terminal state
    }

    def __init__(
        self, db_adapter: RunDatabaseAdapter, get_timestamp: Callable[[], str]
    ):
        """Initialize repository with injected dependencies.

        Args:
            db_adapter: Database adapter for run operations
            get_timestamp: Function that returns current timestamp as string
        """
        self._db_adapter = db_adapter
        self._get_timestamp = get_timestamp

    def create_run(self, config: RunConfig) -> Run:
        """Create a new run in SQLite.

        Args:
            config: Configuration for the run

        Returns:
            The created Run object

        Raises:
            RunCreationError: If the run cannot be created due to a database error
        """
        ts = self._get_timestamp()
        run_id = f"run_{ts}_{uuid.uuid4()}"

        run = Run(
            run_id=run_id,
            created_at=ts,
            total_turns=config.num_turns,
            total_agents=config.num_agents,
            started_at=ts,
            status=RunStatus.RUNNING,
        )
        try:
            self._db_adapter.write_run(run)
        except Exception as e:
            raise RunCreationError(run_id, str(e)) from e
        return run

    def get_run(self, run_id: str) -> Optional[Run]:
        """Get a run from SQLite.

        Args:
            run_id: Unique identifier for the run

        Returns:
            Run model if found, None otherwise

        Raises:
            ValueError: If run_id is empty or None
        """
        validate_run_id(run_id)
        return self._db_adapter.read_run(run_id)

    def list_runs(self) -> list[Run]:
        """List all runs from SQLite."""
        return self._db_adapter.read_all_runs()

    def update_run_status(self, run_id: str, status: RunStatus) -> None:
        """Update run status in SQLite.

        Args:
            run_id: Unique identifier for the run to update
            status: New RunStatus enum value

        Raises:
            ValueError: If run_id is empty or status is None
            RunNotFoundError: If the run with the given ID does not exist
            InvalidTransitionError: If the status transition is invalid
            RunStatusUpdateError: If the status update fails due to a database error
        """
        try:
            # Validate input parameters
            validate_run_id(run_id)

            # Get current run to validate state transition
            current_run = self.get_run(run_id)
            validate_run_exists(run=current_run, run_id=run_id)

            # Validate the status transition
            current_status = current_run.status # type: ignore
            validate_run_status_transition(
                run_id=run_id,
                current_status=current_status,
                target_status=status,
                valid_transitions=self.VALID_TRANSITIONS,
            )

            # Update the run status, once validated.
            ts = self._get_timestamp()
            completed_at = ts if status == RunStatus.COMPLETED else None
            self._db_adapter.update_run_status(run_id, status.value, completed_at)

        except (RunNotFoundError, InvalidTransitionError):
            # Re-raise domain exceptions as-is
            raise
        except Exception as e:
            raise RunStatusUpdateError(run_id, str(e)) from e

    def get_turn_metadata(
        self, run_id: str, turn_number: int
    ) -> Optional[TurnMetadata]:
        """Get turn metadata for a specific run and turn.

        Args:
            run_id: The ID of the run
            turn_number: The turn number (0-indexed)

        Returns:
            TurnMetadata if found, None otherwise

        Raises:
            ValueError: If run_id is empty or turn_number is negative
            ValueError: If the turn metadata data is invalid
            KeyError: If required columns are missing from the database row
            Exception: Database-specific exceptions from the adapter
        """
        validate_run_id(run_id)
        validate_turn_number(turn_number)

        return self._db_adapter.read_turn_metadata(run_id, turn_number)

    def write_turn_metadata(self, turn_metadata: TurnMetadata) -> None:
        """Write turn metadata to the database.

        Args:
            turn_metadata: TurnMetadata model to write

        Raises:
            RunNotFoundError: If the run with the given run_id does not exist
            ValueError: If turn_number is out of bounds for the run
            DuplicateTurnMetadataError: If turn metadata already exists
            Exception: Database-specific exception if constraints are violated or
                      the operation fails. Implementations should document the
                      specific exception types they raise.

        Note:
            TurnMetadata Pydantic model already validates that run_id is non-empty
            and turn_number is non-negative. This method validates:
            - Run exists in the database
            - turn_number is within bounds (0 to run.total_turns - 1)

            Our implementation assumes a setup where we first write a record
            for the run itself, and then we write the subsequent turn records.
            No run = no records.
        """
        # Validate run exists
        run = self.get_run(turn_metadata.run_id)

        validate_run_exists(run=run, run_id=turn_metadata.run_id)

        validate_turn_number_less_than_max_turns(
            turn_number=turn_metadata.turn_number,
            max_turns=run.total_turns, # type: ignore
        )

        self._db_adapter.write_turn_metadata(turn_metadata)


def create_sqlite_repository() -> SQLiteRunRepository:
    """Factory function to create a SQLiteRunRepository with default dependencies.

    Returns:
        SQLiteRunRepository configured with SQLite adapter and default timestamp function
    """
    from db.adapters.sqlite import SQLiteRunAdapter
    from lib.utils import get_current_timestamp

    return SQLiteRunRepository(
        db_adapter=SQLiteRunAdapter(), get_timestamp=get_current_timestamp
    )
