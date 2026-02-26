"""SQLite implementation of run repositories."""

import uuid

from db.adapters.base import RunDatabaseAdapter, TransactionProvider
from db.repositories.interfaces import RunRepository
from lib.timestamp_utils import get_current_timestamp
from lib.validation_decorators import validate_inputs
from simulation.core.metrics.defaults import get_default_metric_keys
from simulation.core.models.runs import Run, RunConfig, RunStatus
from simulation.core.models.turns import TurnMetadata
from simulation.core.utils.exceptions import (
    InvalidTransitionError,
    RunCreationError,
    RunNotFoundError,
    RunStatusUpdateError,
)
from simulation.core.utils.validators import (
    validate_run_exists,
    validate_run_id,
    validate_run_status_transition,
    validate_turn_number,
    validate_turn_number_less_than_max_turns,
)


class SQLiteRunRepository(RunRepository):
    """SQLite implementation of RunRepository.

    Uses dependency injection to accept a database adapter.
    """

    # Valid state transitions for run status
    VALID_TRANSITIONS = {
        RunStatus.RUNNING: {RunStatus.COMPLETED, RunStatus.FAILED},
        RunStatus.COMPLETED: set(),  # Terminal state
        RunStatus.FAILED: set(),  # Terminal state
    }

    def __init__(
        self,
        *,
        db_adapter: RunDatabaseAdapter,
        transaction_provider: TransactionProvider,
    ):
        """Initialize repository with injected dependencies.

        Args:
            db_adapter: Database adapter for run operations
            transaction_provider: Provider for transactions when conn is not passed
        """
        self._db_adapter = db_adapter
        self._transaction_provider = transaction_provider

    def create_run(
        self, config: RunConfig, created_by_app_user_id: str | None = None
    ) -> Run:
        """Create a new run in SQLite.

        Args:
            config: Configuration for the run
            created_by_app_user_id: Optional app_user id for attribution

        Returns:
            The created Run object

        Raises:
            RunCreationError: If the run cannot be created due to a database error
        """
        run_id = "unknown_run"
        try:
            ts = get_current_timestamp()
            run_id = f"run_{ts}_{uuid.uuid4()}"

            metric_keys: list[str]
            if config.metric_keys is None or len(config.metric_keys) == 0:
                metric_keys = get_default_metric_keys()
            else:
                metric_keys = config.metric_keys

            run = Run(
                run_id=run_id,
                app_user_id=created_by_app_user_id,
                created_at=ts,
                total_turns=config.num_turns,
                total_agents=config.num_agents,
                feed_algorithm=config.feed_algorithm,
                metric_keys=metric_keys,
                started_at=ts,
                status=RunStatus.RUNNING,
            )
            with self._transaction_provider.run_transaction() as c:
                self._db_adapter.write_run(run, conn=c)
            return run
        except Exception as e:
            raise RunCreationError(run_id, str(e)) from e

    @validate_inputs((validate_run_id, "run_id"))
    def get_run(self, run_id: str) -> Run | None:
        """Get a run from SQLite.

        Args:
            run_id: Unique identifier for the run

        Returns:
            Run model if found, None otherwise

        Raises:
            ValueError: If run_id is empty or None
        """
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_run(run_id, conn=c)

    def list_runs(self) -> list[Run]:
        """List all runs from SQLite."""
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_all_runs(conn=c)

    def update_run_status(
        self,
        run_id: str,
        status: RunStatus,
        conn: object | None = None,
    ) -> None:
        """Update run status in SQLite.

        Args:
            run_id: Unique identifier for the run to update
            status: New RunStatus enum value
            conn: Optional connection for transactional use; when provided,
                  forwarded to adapter (no commit by adapter).

        Raises:
            ValueError: If run_id is empty or status is None
            RunNotFoundError: If the run with the given ID does not exist
            InvalidTransitionError: If the status transition is invalid
            RunStatusUpdateError: If the status update fails due to a database error
        """
        try:
            # Validate input parameters
            validated_run_id: str = validate_run_id(run_id)

            # Get current run to validate state transition
            current_run = self.get_run(validated_run_id)
            validate_run_exists(run=current_run, run_id=validated_run_id)

            # Validate the status transition
            current_status = current_run.status  # type: ignore
            validate_run_status_transition(
                run_id=validated_run_id,
                current_status=current_status,
                target_status=status,
                valid_transitions=self.VALID_TRANSITIONS,
            )

            # Update the run status, once validated.
            ts = get_current_timestamp()
            completed_at = ts if status == RunStatus.COMPLETED else None
            if conn is not None:
                self._db_adapter.update_run_status(
                    validated_run_id,
                    status.value,
                    completed_at=completed_at,
                    conn=conn,
                )
            else:
                with self._transaction_provider.run_transaction() as c:
                    self._db_adapter.update_run_status(
                        validated_run_id,
                        status.value,
                        completed_at=completed_at,
                        conn=c,
                    )

        except (RunNotFoundError, InvalidTransitionError):
            # Re-raise domain exceptions as-is
            raise
        except Exception as e:
            raise RunStatusUpdateError(run_id, str(e)) from e

    @validate_inputs((validate_run_id, "run_id"), (validate_turn_number, "turn_number"))
    def get_turn_metadata(self, run_id: str, turn_number: int) -> TurnMetadata | None:
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
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_turn_metadata(run_id, turn_number, conn=c)

    @validate_inputs((validate_run_id, "run_id"))
    def list_turn_metadata(self, run_id: str) -> list[TurnMetadata]:
        """List all turn metadata for a run in turn order.

        Args:
            run_id: The ID of the run

        Returns:
            List of TurnMetadata ordered by turn_number ascending.
            Returns empty list if no metadata exists for this run.

        Raises:
            ValueError: If run_id is empty
            ValueError: If turn metadata data is invalid
            KeyError: If required columns are missing from the database row
            Exception: Database-specific exceptions from the adapter
        """
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_turn_metadata_for_run(run_id, conn=c)

    def write_turn_metadata(
        self,
        turn_metadata: TurnMetadata,
        conn: object | None = None,
    ) -> None:
        """Write turn metadata to the database.

        Args:
            turn_metadata: TurnMetadata model to write
            conn: Optional connection for transactional use; when provided,
                  forwarded to adapter (no commit by adapter).

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
            max_turns=run.total_turns,  # type: ignore
        )

        if conn is not None:
            self._db_adapter.write_turn_metadata(turn_metadata, conn=conn)
        else:
            with self._transaction_provider.run_transaction() as c:
                self._db_adapter.write_turn_metadata(turn_metadata, conn=c)


def create_sqlite_repository(
    *,
    transaction_provider: TransactionProvider,
) -> SQLiteRunRepository:
    """Factory function to create a SQLiteRunRepository with default dependencies.

    Returns:
        SQLiteRunRepository configured with SQLite adapter
    """
    from db.adapters.sqlite import SQLiteRunAdapter

    return SQLiteRunRepository(
        db_adapter=SQLiteRunAdapter(),
        transaction_provider=transaction_provider,
    )
