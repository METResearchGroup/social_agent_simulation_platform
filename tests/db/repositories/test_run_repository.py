"""Tests for db.repositories.run_repository module."""

import uuid
from unittest.mock import Mock, patch

import pytest

from db.adapters.base import RunDatabaseAdapter
from db.exceptions import (
    DuplicateTurnMetadataError,
    InvalidTransitionError,
    RunCreationError,
    RunNotFoundError,
    RunStatusUpdateError,
)
from db.repositories.run_repository import SQLiteRunRepository as _SQLiteRunRepository
from simulation.core.models.actions import TurnAction
from simulation.core.models.runs import Run, RunConfig, RunStatus
from simulation.core.models.turns import TurnMetadata


class SQLiteRunRepository(_SQLiteRunRepository):
    """Test-only shim that patches timestamp function from injected mock."""

    def __init__(self, db_adapter: RunDatabaseAdapter, get_timestamp: Mock | None = None):
        super().__init__(db_adapter)
        self._mock_get_timestamp = get_timestamp

    def create_run(self, config: RunConfig) -> Run:
        if self._mock_get_timestamp is None:
            return super().create_run(config)
        with patch(
            "db.repositories.run_repository.get_current_timestamp",
            self._mock_get_timestamp,
        ):
            return super().create_run(config)

    def update_run_status(self, run_id: str, status: RunStatus) -> None:
        if self._mock_get_timestamp is None:
            return super().update_run_status(run_id, status)
        with patch(
            "db.repositories.run_repository.get_current_timestamp",
            self._mock_get_timestamp,
        ):
            return super().update_run_status(run_id, status)


def make_turn_metadata(
    run_id: str = "run_123",
    turn_number: int = 0,
    total_actions: dict[TurnAction, int] | None = None,
    created_at: str = "2024_01_01-12:00:00",
) -> TurnMetadata:
    """Helper factory to create TurnMetadata instances for testing.

    Args:
        run_id: The run ID (default: "run_123")
        turn_number: The turn number (default: 0)
        total_actions: Dictionary mapping action types to counts (default: empty dict)
        created_at: Creation timestamp (default: "2024_01_01-12:00:00")

    Returns:
        TurnMetadata instance with specified values
    """
    if total_actions is None:
        total_actions = {}
    return TurnMetadata(
        run_id=run_id,
        turn_number=turn_number,
        total_actions=total_actions,
        created_at=created_at,
    )


class TestSQLiteRunRepositoryCreateRun:
    """Tests for SQLiteRunRepository.create_run method."""

    def test_creates_run_with_correct_config_values(self):
        """Test that create_run creates a run with correct configuration values."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-12:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        config = RunConfig(num_agents=5, num_turns=10, feed_algorithm="chronological")
        expected_timestamp = "2024_01_01-12:00:00"
        mock_uuid_val = uuid.UUID("12345678-1234-5678-9012-123456789012")

        with patch(
            "db.repositories.run_repository.uuid.uuid4", return_value=mock_uuid_val
        ):
            # Act
            result = repo.create_run(config)

            # Assert
            expected_run_id = f"run_{expected_timestamp}_{mock_uuid_val}"
            assert result.run_id == expected_run_id
            assert result.created_at == expected_timestamp
            assert result.total_turns == 10
            assert result.total_agents == 5
            assert result.started_at == expected_timestamp
            assert result.status == RunStatus.RUNNING
            assert result.completed_at is None
            mock_adapter.write_run.assert_called_once()

    def test_creates_run_with_different_config_values(self):
        """Test that create_run handles different configuration values correctly."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_02_15-15:30:45")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        config = RunConfig(num_agents=20, num_turns=50, feed_algorithm="chronological")
        expected_timestamp = "2024_02_15-15:30:45"
        mock_uuid_val = uuid.UUID("00000000-0000-0000-0000-000000000000")

        with patch(
            "db.repositories.run_repository.uuid.uuid4", return_value=mock_uuid_val
        ):
            # Act
            result = repo.create_run(config)

            # Assert
            assert result.total_agents == 20
            assert result.total_turns == 50
            assert result.run_id.startswith(f"run_{expected_timestamp}_")

    def test_persists_run_to_database(self):
        """Test that create_run persists the run to the database via write_run."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-12:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        config = RunConfig(num_agents=5, num_turns=10, feed_algorithm="chronological")

        # Act
        result = repo.create_run(config)

        # Assert
        mock_adapter.write_run.assert_called_once()
        call_args = mock_adapter.write_run.call_args[0][0]
        assert isinstance(call_args, Run)
        assert call_args.run_id == result.run_id
        assert call_args.total_agents == 5
        assert call_args.total_turns == 10
        assert call_args.status == RunStatus.RUNNING

    def test_generates_unique_run_id_with_timestamp(self):
        """Test that create_run generates a unique run_id using timestamp and UUID."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        timestamp1 = "2024_01_01-12:00:00"
        timestamp2 = "2024_01_01-12:00:01"
        mock_get_timestamp = Mock(side_effect=[timestamp1, timestamp2])
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        config = RunConfig(num_agents=5, num_turns=10, feed_algorithm="chronological")
        uuid1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
        uuid2 = uuid.UUID("22222222-2222-2222-2222-222222222222")

        with patch(
            "db.repositories.run_repository.uuid.uuid4", side_effect=[uuid1, uuid2]
        ):
            # Act
            result1 = repo.create_run(config)
            result2 = repo.create_run(config)

            # Assert
            assert result1.run_id == f"run_{timestamp1}_{uuid1}"
            assert result2.run_id == f"run_{timestamp2}_{uuid2}"
            assert result1.run_id != result2.run_id

    def test_sets_status_to_running_on_creation(self):
        """Test that create_run always sets status to RUNNING."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-12:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        config = RunConfig(num_agents=5, num_turns=10, feed_algorithm="chronological")

        # Act
        result = repo.create_run(config)

        # Assert
        assert result.status == RunStatus.RUNNING

    def test_sets_completed_at_to_none_on_creation(self):
        """Test that create_run sets completed_at to None for new runs."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-12:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        config = RunConfig(num_agents=5, num_turns=10, feed_algorithm="chronological")

        # Act
        result = repo.create_run(config)

        # Assert
        assert result.completed_at is None

    def test_raises_run_creation_error_when_write_run_fails(self):
        """Test that create_run raises RunCreationError when database write fails."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        expected_timestamp = "2024_01_01-12:00:00"
        mock_get_timestamp = Mock(return_value=expected_timestamp)
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        config = RunConfig(num_agents=5, num_turns=10, feed_algorithm="chronological")
        mock_uuid_val = uuid.UUID("12345678-1234-5678-9012-123456789012")
        expected_run_id = f"run_{expected_timestamp}_{mock_uuid_val}"
        db_error = Exception("Database connection failed")
        mock_adapter.write_run.side_effect = db_error

        with patch(
            "db.repositories.run_repository.uuid.uuid4", return_value=mock_uuid_val
        ):
            # Act & Assert
            with pytest.raises(RunCreationError) as exc_info:
                repo.create_run(config)

            assert exc_info.value.run_id == expected_run_id
            assert "Database connection failed" in str(exc_info.value.reason)
            assert isinstance(exc_info.value.__cause__, Exception)

    def test_raises_run_creation_error_with_correct_run_id_in_message(self):
        """Test that RunCreationError includes the correct run_id in the error message."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        expected_timestamp = "2024_01_01-12:00:00"
        mock_get_timestamp = Mock(return_value=expected_timestamp)
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        config = RunConfig(num_agents=5, num_turns=10, feed_algorithm="chronological")
        mock_uuid_val = uuid.UUID("12345678-1234-5678-9012-123456789012")
        expected_run_id = f"run_{expected_timestamp}_{mock_uuid_val}"
        mock_adapter.write_run.side_effect = Exception("DB error")

        with patch(
            "db.repositories.run_repository.uuid.uuid4", return_value=mock_uuid_val
        ):
            # Act & Assert
            with pytest.raises(RunCreationError) as exc_info:
                repo.create_run(config)

            assert exc_info.value.run_id == expected_run_id
            assert "DB error" in str(exc_info.value.reason)

    def test_preserves_original_exception_in_run_creation_error(self):
        """Test that the original exception is preserved as the cause of RunCreationError."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-12:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        config = RunConfig(num_agents=5, num_turns=10, feed_algorithm="chronological")
        original_error = ValueError("Invalid data")
        mock_adapter.write_run.side_effect = original_error

        # Act & Assert
        with pytest.raises(RunCreationError) as exc_info:
            repo.create_run(config)

        assert exc_info.value.__cause__ is original_error


class TestSQLiteRunRepositoryGetRun:
    """Tests for SQLiteRunRepository.get_run method."""

    def test_returns_run_when_found(self):
        """Test that get_run returns a Run when it exists in the database."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-12:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        run_id = "run_123"
        expected = Run(
            run_id=run_id,
            created_at="2024_01_01-12:00:00",
            total_turns=10,
            total_agents=5,
            started_at="2024_01_01-12:00:00",
            status=RunStatus.RUNNING,
            completed_at=None,
        )
        mock_adapter.read_run.return_value = expected

        # Act
        result = repo.get_run(run_id)

        # Assert
        assert result is not None
        assert result.run_id == expected.run_id
        assert result.created_at == expected.created_at
        assert result.total_turns == expected.total_turns
        assert result.total_agents == expected.total_agents
        assert result.started_at == expected.started_at
        assert result.status == expected.status
        assert result.completed_at == expected.completed_at
        mock_adapter.read_run.assert_called_once_with(run_id)

    def test_returns_none_when_run_not_found(self):
        """Test that get_run returns None when run does not exist."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-12:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        run_id = "nonexistent_run"
        mock_adapter.read_run.return_value = None

        # Act
        result = repo.get_run(run_id)

        # Assert
        assert result is None
        mock_adapter.read_run.assert_called_once_with(run_id)

    def test_calls_read_run_with_correct_run_id(self):
        """Test that get_run calls read_run with the correct run_id parameter."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-12:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        run_id = "run_123"
        mock_adapter.read_run.return_value = None

        # Act
        repo.get_run(run_id)

        # Assert
        mock_adapter.read_run.assert_called_once_with(run_id)

    def test_returns_completed_run_correctly(self):
        """Test that get_run returns a completed run with completed_at timestamp."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-12:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        run_id = "run_123"
        expected = Run(
            run_id=run_id,
            created_at="2024_01_01-12:00:00",
            total_turns=10,
            total_agents=5,
            started_at="2024_01_01-12:00:00",
            status=RunStatus.COMPLETED,
            completed_at="2024_01_01-13:00:00",
        )
        mock_adapter.read_run.return_value = expected

        # Act
        result = repo.get_run(run_id)

        # Assert
        assert result is not None
        assert result.status == RunStatus.COMPLETED
        assert result.completed_at == "2024_01_01-13:00:00"

    def test_returns_failed_run_correctly(self):
        """Test that get_run returns a failed run correctly."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-12:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        run_id = "run_123"
        expected = Run(
            run_id=run_id,
            created_at="2024_01_01-12:00:00",
            total_turns=10,
            total_agents=5,
            started_at="2024_01_01-12:00:00",
            status=RunStatus.FAILED,
            completed_at=None,
        )
        mock_adapter.read_run.return_value = expected

        # Act
        result = repo.get_run(run_id)

        # Assert
        assert result is not None
        assert result.status == RunStatus.FAILED


class TestSQLiteRunRepositoryListRuns:
    """Tests for SQLiteRunRepository.list_runs method."""

    def test_returns_empty_list_when_no_runs_exist(self):
        """Test that list_runs returns an empty list when no runs exist."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-12:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        expected = []
        mock_adapter.read_all_runs.return_value = expected

        # Act
        result = repo.list_runs()

        # Assert
        assert result == expected
        assert isinstance(result, list)
        assert len(result) == 0
        mock_adapter.read_all_runs.assert_called_once()

    def test_returns_all_runs_when_runs_exist(self):
        """Test that list_runs returns all runs from the database."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-12:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        expected = [
            Run(
                run_id="run_1",
                created_at="2024_01_01-12:00:00",
                total_turns=10,
                total_agents=5,
                started_at="2024_01_01-12:00:00",
                status=RunStatus.COMPLETED,
                completed_at="2024_01_01-13:00:00",
            ),
            Run(
                run_id="run_2",
                created_at="2024_01_02-12:00:00",
                total_turns=20,
                total_agents=10,
                started_at="2024_01_02-12:00:00",
                status=RunStatus.RUNNING,
                completed_at=None,
            ),
        ]
        mock_adapter.read_all_runs.return_value = expected

        # Act
        result = repo.list_runs()

        # Assert
        assert len(result) == 2
        assert result[0].run_id == "run_1"
        assert result[1].run_id == "run_2"

    def test_returns_runs_in_correct_order(self):
        """Test that list_runs returns runs in the order provided by read_all_runs."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-12:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        expected = [
            Run(
                run_id="run_newest",
                created_at="2024_01_03-12:00:00",
                total_turns=10,
                total_agents=5,
                started_at="2024_01_03-12:00:00",
                status=RunStatus.RUNNING,
                completed_at=None,
            ),
            Run(
                run_id="run_oldest",
                created_at="2024_01_01-12:00:00",
                total_turns=10,
                total_agents=5,
                started_at="2024_01_01-12:00:00",
                status=RunStatus.COMPLETED,
                completed_at="2024_01_01-13:00:00",
            ),
        ]
        mock_adapter.read_all_runs.return_value = expected

        # Act
        result = repo.list_runs()

        # Assert
        assert result[0].run_id == "run_newest"
        assert result[1].run_id == "run_oldest"

    def test_calls_read_all_runs_once(self):
        """Test that list_runs calls read_all_runs exactly once."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-12:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        mock_adapter.read_all_runs.return_value = []

        # Act
        repo.list_runs()

        # Assert
        mock_adapter.read_all_runs.assert_called_once()

    def test_handles_large_number_of_runs(self):
        """Test that list_runs handles a large number of runs correctly."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-12:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        expected = [
            Run(
                run_id=f"run_{i}",
                created_at=f"2024_01_{i:02d}-12:00:00",
                total_turns=10,
                total_agents=5,
                started_at=f"2024_01_{i:02d}-12:00:00",
                status=RunStatus.RUNNING,
                completed_at=None,
            )
            for i in range(100)
        ]
        mock_adapter.read_all_runs.return_value = expected

        # Act
        result = repo.list_runs()

        # Assert
        assert len(result) == 100
        assert all(isinstance(run, Run) for run in result)


class TestSQLiteRunRepositoryUpdateRunStatus:
    """Tests for SQLiteRunRepository.update_run_status method."""

    def test_updates_status_to_completed(self):
        """Test that update_run_status updates status to COMPLETED correctly."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        expected_timestamp = "2024_01_01-13:00:00"
        mock_get_timestamp = Mock(return_value=expected_timestamp)
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        run_id = "run_123"
        status = RunStatus.COMPLETED
        current_run = Run(
            run_id=run_id,
            created_at="2024_01_01-12:00:00",
            total_turns=10,
            total_agents=5,
            started_at="2024_01_01-12:00:00",
            status=RunStatus.RUNNING,
            completed_at=None,
        )
        mock_adapter.read_run.return_value = current_run

        # Act
        repo.update_run_status(run_id, status)

        # Assert
        # Verify that status enum is converted to string value
        mock_adapter.update_run_status.assert_called_once()
        call_args = mock_adapter.update_run_status.call_args[0]
        assert call_args[0] == run_id
        assert call_args[1] == status.value  # Enum value (string) is passed
        assert call_args[2] == expected_timestamp

    def test_updates_status_to_failed_without_completed_at(self):
        """Test that update_run_status sets completed_at to None for FAILED status."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-13:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        run_id = "run_123"
        status = RunStatus.FAILED
        current_run = Run(
            run_id=run_id,
            created_at="2024_01_01-12:00:00",
            total_turns=10,
            total_agents=5,
            started_at="2024_01_01-12:00:00",
            status=RunStatus.RUNNING,
            completed_at=None,
        )
        mock_adapter.read_run.return_value = current_run

        # Act
        repo.update_run_status(run_id, status)

        # Assert
        mock_adapter.update_run_status.assert_called_once_with(
            run_id, status.value, None
        )

    def test_updates_status_to_running_without_completed_at(self):
        """Test that update_run_status sets completed_at to None for RUNNING status."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-13:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        run_id = "run_123"
        status = RunStatus.RUNNING
        current_run = Run(
            run_id=run_id,
            created_at="2024_01_01-12:00:00",
            total_turns=10,
            total_agents=5,
            started_at="2024_01_01-12:00:00",
            status=RunStatus.RUNNING,
            completed_at=None,
        )
        mock_adapter.read_run.return_value = current_run

        # Act
        repo.update_run_status(run_id, status)

        # Assert
        mock_adapter.update_run_status.assert_called_once_with(
            run_id, status.value, None
        )

    def test_calls_update_run_status_with_correct_parameters_for_completed(self):
        """Test that update_run_status calls db function with correct parameters for COMPLETED."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        expected_timestamp = "2024_01_01-13:00:00"
        mock_get_timestamp = Mock(return_value=expected_timestamp)
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        run_id = "run_123"
        status = RunStatus.COMPLETED
        current_run = Run(
            run_id=run_id,
            created_at="2024_01_01-12:00:00",
            total_turns=10,
            total_agents=5,
            started_at="2024_01_01-12:00:00",
            status=RunStatus.RUNNING,
            completed_at=None,
        )
        mock_adapter.read_run.return_value = current_run

        # Act
        repo.update_run_status(run_id, status)

        # Assert
        mock_adapter.update_run_status.assert_called_once()
        call_args = mock_adapter.update_run_status.call_args[0]
        assert call_args[0] == run_id
        assert call_args[1] == status.value  # Enum value (string) is passed
        assert call_args[2] == expected_timestamp

    def test_calls_update_run_status_with_correct_parameters_for_failed(self):
        """Test that update_run_status calls db function with correct parameters for FAILED."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-13:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        run_id = "run_123"
        status = RunStatus.FAILED
        current_run = Run(
            run_id=run_id,
            created_at="2024_01_01-12:00:00",
            total_turns=10,
            total_agents=5,
            started_at="2024_01_01-12:00:00",
            status=RunStatus.RUNNING,
            completed_at=None,
        )
        mock_adapter.read_run.return_value = current_run

        # Act
        repo.update_run_status(run_id, status)

        # Assert
        mock_adapter.update_run_status.assert_called_once()
        call_args = mock_adapter.update_run_status.call_args[0]
        assert call_args[0] == run_id
        assert call_args[1] == status.value  # Enum value (string) is passed
        assert call_args[2] is None

    def test_uses_current_timestamp_for_completed_status(self):
        """Test that update_run_status uses get_current_timestamp for COMPLETED status."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        timestamp1 = "2024_01_01-13:00:00"
        timestamp2 = "2024_01_01-14:00:00"
        mock_get_timestamp = Mock(side_effect=[timestamp1, timestamp2])
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        run_id = "run_123"
        status = RunStatus.COMPLETED
        current_run = Run(
            run_id=run_id,
            created_at="2024_01_01-12:00:00",
            total_turns=10,
            total_agents=5,
            started_at="2024_01_01-12:00:00",
            status=RunStatus.RUNNING,
            completed_at=None,
        )
        mock_adapter.read_run.return_value = current_run

        # Act
        repo.update_run_status(run_id, status)

        # Assert
        mock_adapter.update_run_status.assert_called_once_with(
            run_id, status.value, timestamp1
        )

    def test_handles_valid_transitions_from_running(self):
        """Test that update_run_status handles all valid transitions from RUNNING status."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-13:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        run_id = "run_123"
        current_run = Run(
            run_id=run_id,
            created_at="2024_01_01-12:00:00",
            total_turns=10,
            total_agents=5,
            started_at="2024_01_01-12:00:00",
            status=RunStatus.RUNNING,
            completed_at=None,
        )

        # Valid transitions from RUNNING: idempotent (RUNNING), COMPLETED, and FAILED
        valid_target_statuses = [
            RunStatus.RUNNING,
            RunStatus.COMPLETED,
            RunStatus.FAILED,
        ]

        for status in valid_target_statuses:
            mock_adapter.read_run.return_value = current_run
            mock_adapter.update_run_status.reset_mock()
            # Act
            repo.update_run_status(run_id, status)

            # Assert
            expected_completed_at = (
                "2024_01_01-13:00:00" if status == RunStatus.COMPLETED else None
            )
            mock_adapter.update_run_status.assert_called_once_with(
                run_id, status.value, expected_completed_at
            )


class TestSQLiteRunRepositoryStateMachineValidation:
    """Tests for state machine validation in update_run_status."""

    def test_allows_transition_from_running_to_completed(self):
        """Test that RUNNING -> COMPLETED transition is allowed."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-13:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        run_id = "run_123"
        current_run = Run(
            run_id=run_id,
            created_at="2024_01_01-12:00:00",
            total_turns=10,
            total_agents=5,
            started_at="2024_01_01-12:00:00",
            status=RunStatus.RUNNING,
            completed_at=None,
        )
        mock_adapter.read_run.return_value = current_run

        # Act
        repo.update_run_status(run_id, RunStatus.COMPLETED)

        # Assert
        mock_adapter.update_run_status.assert_called_once()

    def test_allows_transition_from_running_to_failed(self):
        """Test that RUNNING -> FAILED transition is allowed."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-13:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        run_id = "run_123"
        current_run = Run(
            run_id=run_id,
            created_at="2024_01_01-12:00:00",
            total_turns=10,
            total_agents=5,
            started_at="2024_01_01-12:00:00",
            status=RunStatus.RUNNING,
            completed_at=None,
        )
        mock_adapter.read_run.return_value = current_run

        # Act
        repo.update_run_status(run_id, RunStatus.FAILED)

        # Assert
        mock_adapter.update_run_status.assert_called_once()

    def test_allows_idempotent_status_update(self):
        """Test that setting the same status is allowed (idempotent operation)."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-14:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        run_id = "run_123"
        current_run = Run(
            run_id=run_id,
            created_at="2024_01_01-12:00:00",
            total_turns=10,
            total_agents=5,
            started_at="2024_01_01-12:00:00",
            status=RunStatus.COMPLETED,
            completed_at="2024_01_01-13:00:00",
        )
        mock_adapter.read_run.return_value = current_run

        # Act
        repo.update_run_status(run_id, RunStatus.COMPLETED)

        # Assert
        mock_adapter.update_run_status.assert_called_once()

    def test_rejects_transition_from_completed_to_failed(self):
        """Test that COMPLETED -> FAILED transition is rejected."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-13:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        run_id = "run_123"
        current_run = Run(
            run_id=run_id,
            created_at="2024_01_01-12:00:00",
            total_turns=10,
            total_agents=5,
            started_at="2024_01_01-12:00:00",
            status=RunStatus.COMPLETED,
            completed_at="2024_01_01-13:00:00",
        )
        mock_adapter.read_run.return_value = current_run

        # Act & Assert
        with pytest.raises(InvalidTransitionError) as exc_info:
            repo.update_run_status(run_id, RunStatus.FAILED)

        assert exc_info.value.run_id == run_id
        assert exc_info.value.current_status == "completed"
        assert exc_info.value.target_status == "failed"
        assert exc_info.value.valid_transitions is None

    def test_rejects_transition_from_completed_to_running(self):
        """Test that COMPLETED -> RUNNING transition is rejected."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-13:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        run_id = "run_123"
        current_run = Run(
            run_id=run_id,
            created_at="2024_01_01-12:00:00",
            total_turns=10,
            total_agents=5,
            started_at="2024_01_01-12:00:00",
            status=RunStatus.COMPLETED,
            completed_at="2024_01_01-13:00:00",
        )
        mock_adapter.read_run.return_value = current_run

        # Act & Assert
        with pytest.raises(InvalidTransitionError) as exc_info:
            repo.update_run_status(run_id, RunStatus.RUNNING)

        assert exc_info.value.run_id == run_id
        assert exc_info.value.current_status == "completed"
        assert exc_info.value.target_status == "running"

    def test_rejects_transition_from_failed_to_completed(self):
        """Test that FAILED -> COMPLETED transition is rejected."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-13:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        run_id = "run_123"
        current_run = Run(
            run_id=run_id,
            created_at="2024_01_01-12:00:00",
            total_turns=10,
            total_agents=5,
            started_at="2024_01_01-12:00:00",
            status=RunStatus.FAILED,
            completed_at=None,
        )
        mock_adapter.read_run.return_value = current_run

        # Act & Assert
        with pytest.raises(InvalidTransitionError) as exc_info:
            repo.update_run_status(run_id, RunStatus.COMPLETED)

        assert exc_info.value.run_id == run_id
        assert exc_info.value.current_status == "failed"
        assert exc_info.value.target_status == "completed"

    def test_rejects_transition_from_failed_to_running(self):
        """Test that FAILED -> RUNNING transition is rejected."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-13:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        run_id = "run_123"
        current_run = Run(
            run_id=run_id,
            created_at="2024_01_01-12:00:00",
            total_turns=10,
            total_agents=5,
            started_at="2024_01_01-12:00:00",
            status=RunStatus.FAILED,
            completed_at=None,
        )
        mock_adapter.read_run.return_value = current_run

        # Act & Assert
        with pytest.raises(InvalidTransitionError) as exc_info:
            repo.update_run_status(run_id, RunStatus.RUNNING)

        assert exc_info.value.run_id == run_id
        assert exc_info.value.current_status == "failed"
        assert exc_info.value.target_status == "running"

    def test_error_message_includes_current_and_target_status(self):
        """Test that error message includes both current and target status."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-13:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        run_id = "run_123"
        current_run = Run(
            run_id=run_id,
            created_at="2024_01_01-12:00:00",
            total_turns=10,
            total_agents=5,
            started_at="2024_01_01-12:00:00",
            status=RunStatus.COMPLETED,
            completed_at="2024_01_01-13:00:00",
        )
        mock_adapter.read_run.return_value = current_run

        # Act & Assert
        with pytest.raises(InvalidTransitionError) as exc_info:
            repo.update_run_status(run_id, RunStatus.FAILED)

        error_message = str(exc_info.value)
        assert "completed" in error_message.lower()
        assert "failed" in error_message.lower()
        assert run_id in error_message
        assert exc_info.value.current_status == "completed"
        assert exc_info.value.target_status == "failed"

    def test_error_message_includes_valid_transitions(self):
        """Test that error message includes information about valid transitions."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-13:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        run_id = "run_123"
        current_run = Run(
            run_id=run_id,
            created_at="2024_01_01-12:00:00",
            total_turns=10,
            total_agents=5,
            started_at="2024_01_01-12:00:00",
            status=RunStatus.COMPLETED,
            completed_at="2024_01_01-13:00:00",
        )
        mock_adapter.read_run.return_value = current_run

        # Act & Assert
        with pytest.raises(InvalidTransitionError) as exc_info:
            repo.update_run_status(run_id, RunStatus.FAILED)

        error_message = str(exc_info.value)
        assert (
            "terminal state" in error_message.lower() or "none" in error_message.lower()
        )
        assert exc_info.value.valid_transitions is None

    def test_raises_run_not_found_error_when_run_not_found(self):
        """Test that RunNotFoundError is raised when run doesn't exist."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-13:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        run_id = "nonexistent_run"
        mock_adapter.read_run.return_value = None

        # Act & Assert
        with pytest.raises(RunNotFoundError) as exc_info:
            repo.update_run_status(run_id, RunStatus.COMPLETED)

        assert exc_info.value.run_id == run_id


class TestDomainExceptions:
    """Tests for domain-specific exceptions."""

    def test_run_not_found_error_has_run_id_attribute(self):
        """Test that RunNotFoundError has run_id attribute."""
        run_id = "test_run_123"
        error = RunNotFoundError(run_id)

        assert error.run_id == run_id
        assert run_id in str(error)

    def test_invalid_transition_error_has_all_attributes(self):
        """Test that InvalidTransitionError has all required attributes."""
        run_id = "test_run_123"
        current_status = "completed"
        target_status = "failed"
        valid_transitions = None

        error = InvalidTransitionError(
            run_id, current_status, target_status, valid_transitions
        )

        assert error.run_id == run_id
        assert error.current_status == current_status
        assert error.target_status == target_status
        assert error.valid_transitions == valid_transitions
        assert run_id in str(error)
        assert current_status in str(error)
        assert target_status in str(error)

    def test_invalid_transition_error_with_valid_transitions_list(self):
        """Test InvalidTransitionError with a list of valid transitions."""
        run_id = "test_run_123"
        current_status = "running"
        target_status = "completed"
        valid_transitions = ["completed", "failed"]

        error = InvalidTransitionError(
            run_id, current_status, target_status, valid_transitions
        )

        assert error.valid_transitions == valid_transitions
        assert "completed" in str(error) or "failed" in str(error)

    def test_run_creation_error_has_attributes(self):
        """Test that RunCreationError has run_id and reason attributes."""
        run_id = "test_run_123"
        reason = "Database connection failed"

        error = RunCreationError(run_id, reason)

        assert error.run_id == run_id
        assert error.reason == reason
        assert run_id in str(error)
        assert reason in str(error)

    def test_run_creation_error_without_reason(self):
        """Test RunCreationError without a reason."""
        run_id = "test_run_123"

        error = RunCreationError(run_id)

        assert error.run_id == run_id
        assert error.reason is None
        assert run_id in str(error)

    def test_run_status_update_error_has_attributes(self):
        """Test that RunStatusUpdateError has run_id and reason attributes."""
        run_id = "test_run_123"
        reason = "Database constraint violation"

        error = RunStatusUpdateError(run_id, reason)

        assert error.run_id == run_id
        assert error.reason == reason
        assert run_id in str(error)
        assert reason in str(error)

    def test_run_status_update_error_without_reason(self):
        """Test RunStatusUpdateError without a reason."""
        run_id = "test_run_123"

        error = RunStatusUpdateError(run_id)

        assert error.run_id == run_id
        assert error.reason is None
        assert run_id in str(error)

    def test_run_status_update_error_when_database_fails(self):
        """Test that RunStatusUpdateError is raised when database update fails."""
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-13:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        run_id = "run_123"
        current_run = Run(
            run_id=run_id,
            created_at="2024_01_01-12:00:00",
            total_turns=10,
            total_agents=5,
            started_at="2024_01_01-12:00:00",
            status=RunStatus.RUNNING,
            completed_at=None,
        )
        db_error = Exception("Database connection lost")
        mock_adapter.read_run.return_value = current_run
        mock_adapter.update_run_status.side_effect = db_error

        with pytest.raises(RunStatusUpdateError) as exc_info:
            repo.update_run_status(run_id, RunStatus.COMPLETED)

        assert exc_info.value.run_id == run_id
        assert "Database connection lost" in str(exc_info.value.reason)
        assert exc_info.value.__cause__ is db_error


class TestSQLiteRunRepositoryGetTurnMetadata:
    """Tests for SQLiteRunRepository.get_turn_metadata method."""

    def test_returns_turn_metadata_when_found(self):
        """Test that get_turn_metadata returns TurnMetadata when it exists."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-12:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        run_id = "run_123"
        turn_number = 0

        expected = TurnMetadata(
            run_id=run_id,
            turn_number=turn_number,
            total_actions={
                TurnAction.LIKE: 5,
                TurnAction.COMMENT: 2,
                TurnAction.FOLLOW: 1,
            },
            created_at="2024_01_01-12:00:00",
        )
        mock_adapter.read_turn_metadata.return_value = expected

        # Act
        result = repo.get_turn_metadata(run_id, turn_number)

        # Assert
        assert result is not None
        assert result.run_id == expected.run_id
        assert result.turn_number == expected.turn_number
        assert result.total_actions == expected.total_actions
        assert result.created_at == expected.created_at
        mock_adapter.read_turn_metadata.assert_called_once_with(run_id, turn_number)

    def test_returns_none_when_not_found(self):
        """Test that get_turn_metadata returns None when metadata doesn't exist."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-12:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        run_id = "run_123"
        turn_number = 0
        mock_adapter.read_turn_metadata.return_value = None

        # Act
        result = repo.get_turn_metadata(run_id, turn_number)

        # Assert
        assert result is None
        mock_adapter.read_turn_metadata.assert_called_once_with(run_id, turn_number)

    def test_raises_valueerror_for_empty_run_id(self):
        """Test that get_turn_metadata raises ValueError for empty run_id."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-12:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        run_id = ""
        turn_number = 0

        # Act & Assert
        with pytest.raises(ValueError, match="run_id is invalid"):
            repo.get_turn_metadata(run_id, turn_number)

        # Verify adapter was not called
        mock_adapter.read_turn_metadata.assert_not_called()

    def test_raises_valueerror_for_whitespace_only_run_id(self):
        """Test that get_turn_metadata raises ValueError for whitespace-only run_id."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-12:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        run_id = "   "
        turn_number = 0

        # Act & Assert
        with pytest.raises(ValueError, match="run_id is invalid"):
            repo.get_turn_metadata(run_id, turn_number)

        # Verify adapter was not called
        mock_adapter.read_turn_metadata.assert_not_called()

    def test_raises_valueerror_for_negative_turn_number(self):
        """Test that get_turn_metadata raises ValueError for negative turn_number."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-12:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        run_id = "run_123"
        turn_number = -1

        # Act & Assert
        with pytest.raises(ValueError, match="turn_number is invalid"):
            repo.get_turn_metadata(run_id, turn_number)

        # Verify adapter was not called
        mock_adapter.read_turn_metadata.assert_not_called()

    def test_propagates_adapter_exceptions(self):
        """Test that get_turn_metadata propagates exceptions from adapter."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-12:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        run_id = "run_123"
        turn_number = 0
        adapter_error = ValueError("Invalid data from adapter")
        mock_adapter.read_turn_metadata.side_effect = adapter_error

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid data from adapter"):
            repo.get_turn_metadata(run_id, turn_number)

    def test_propagates_keyerror_from_adapter(self):
        """Test that get_turn_metadata propagates KeyError raised by adapter."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-12:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        run_id = "run_123"
        turn_number = 0
        adapter_error = KeyError("missing column")
        mock_adapter.read_turn_metadata.side_effect = adapter_error

        # Act & Assert
        with pytest.raises(KeyError, match="missing column"):
            repo.get_turn_metadata(run_id, turn_number)

    def test_calls_adapter_with_correct_parameters(self):
        """Test that get_turn_metadata calls adapter with correct parameters."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-12:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        run_id = "run_123"
        turn_number = 5
        mock_adapter.read_turn_metadata.return_value = None

        # Act
        repo.get_turn_metadata(run_id, turn_number)

        # Assert
        mock_adapter.read_turn_metadata.assert_called_once_with(run_id, turn_number)

    def test_handles_turn_metadata_with_all_action_types(self):
        """Test that get_turn_metadata handles all action types correctly."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-12:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        run_id = "run_123"
        turn_number = 0

        expected = make_turn_metadata(
            run_id=run_id,
            turn_number=turn_number,
            total_actions={
                TurnAction.LIKE: 10,
                TurnAction.COMMENT: 5,
                TurnAction.FOLLOW: 3,
            },
            created_at="2024_01_01-12:00:00",
        )
        mock_adapter.read_turn_metadata.return_value = expected

        # Act
        result = repo.get_turn_metadata(run_id, turn_number)

        # Assert
        assert result is not None
        assert result.run_id == run_id
        assert result.turn_number == turn_number
        assert result.created_at == "2024_01_01-12:00:00"
        assert result.total_actions[TurnAction.LIKE] == 10
        assert result.total_actions[TurnAction.COMMENT] == 5
        assert result.total_actions[TurnAction.FOLLOW] == 3

    def test_handles_turn_metadata_with_zero_actions(self):
        """Test that get_turn_metadata handles turn metadata with zero actions."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-12:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        run_id = "run_123"
        turn_number = 0

        expected = make_turn_metadata(
            run_id=run_id,
            turn_number=turn_number,
            total_actions={
                TurnAction.LIKE: 0,
                TurnAction.COMMENT: 0,
                TurnAction.FOLLOW: 0,
            },
            created_at="2024_01_01-12:00:00",
        )
        mock_adapter.read_turn_metadata.return_value = expected

        # Act
        result = repo.get_turn_metadata(run_id, turn_number)

        # Assert
        assert result is not None
        assert result.run_id == run_id
        assert result.turn_number == turn_number
        assert result.created_at == "2024_01_01-12:00:00"
        assert result.total_actions[TurnAction.LIKE] == 0
        assert result.total_actions[TurnAction.COMMENT] == 0
        assert result.total_actions[TurnAction.FOLLOW] == 0


class TestSQLiteRunRepositoryWriteTurnMetadata:
    """Tests for SQLiteRunRepository.write_turn_metadata method."""

    def test_writes_turn_metadata_successfully(self):
        """Test that write_turn_metadata delegates to adapter successfully."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-12:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        run_id = "run_123"
        turn_number = 0

        # Mock get_run to return a proper Run object
        mock_run = Run(
            run_id=run_id,
            created_at="2024_01_01-12:00:00",
            total_turns=5,
            total_agents=3,
            started_at="2024_01_01-12:00:00",
            status=RunStatus.RUNNING,
            completed_at=None,
        )
        repo.get_run = Mock(return_value=mock_run)

        turn_metadata = TurnMetadata(
            run_id=run_id,
            turn_number=turn_number,
            total_actions={
                TurnAction.LIKE: 5,
                TurnAction.COMMENT: 2,
                TurnAction.FOLLOW: 1,
            },
            created_at="2024_01_01-12:00:00",
        )

        # Act
        repo.write_turn_metadata(turn_metadata)

        # Assert
        mock_adapter.write_turn_metadata.assert_called_once_with(turn_metadata)

    def test_raises_run_not_found_error_when_run_does_not_exist(self):
        """Test that write_turn_metadata raises RunNotFoundError when run doesn't exist."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-12:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        run_id = "nonexistent_run"

        # Mock get_run to return None (run doesn't exist)
        repo.get_run = Mock(return_value=None)

        turn_metadata = TurnMetadata(
            run_id=run_id,
            turn_number=0,
            total_actions={TurnAction.LIKE: 5},
            created_at="2024_01_01-12:00:00",
        )

        # Act & Assert
        with pytest.raises(RunNotFoundError) as exc_info:
            repo.write_turn_metadata(turn_metadata)

        assert exc_info.value.run_id == run_id
        # Verify adapter was not called
        mock_adapter.write_turn_metadata.assert_not_called()

    def test_raises_valueerror_when_turn_number_out_of_bounds(self):
        """Test that write_turn_metadata raises ValueError when turn_number is out of bounds."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-12:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        run_id = "run_123"

        # Mock get_run to return a run with 5 turns (0-4)
        mock_run = Run(
            run_id=run_id,
            created_at="2024_01_01-12:00:00",
            total_turns=5,
            total_agents=3,
            started_at="2024_01_01-12:00:00",
            status=RunStatus.RUNNING,
            completed_at=None,
        )
        repo.get_run = Mock(return_value=mock_run)

        # Try to write metadata for turn 5 (out of bounds)
        turn_metadata = TurnMetadata(
            run_id=run_id,
            turn_number=5,  # Out of bounds (should be 0-4)
            total_actions={TurnAction.LIKE: 5},
            created_at="2024_01_01-12:00:00",
        )

        # Act & Assert
        with pytest.raises(
            ValueError, match="Turn number 5 is greater than the maximum number of turns: 5"
        ):
            repo.write_turn_metadata(turn_metadata)

        # Verify adapter was not called
        mock_adapter.write_turn_metadata.assert_not_called()

    def test_propagates_duplicate_turn_metadata_error(self):
        """Test that write_turn_metadata propagates DuplicateTurnMetadataError from adapter."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-12:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        run_id = "run_123"

        # Mock get_run to return a proper Run object
        mock_run = Run(
            run_id=run_id,
            created_at="2024_01_01-12:00:00",
            total_turns=5,
            total_agents=3,
            started_at="2024_01_01-12:00:00",
            status=RunStatus.RUNNING,
            completed_at=None,
        )
        repo.get_run = Mock(return_value=mock_run)

        turn_metadata = TurnMetadata(
            run_id=run_id,
            turn_number=0,
            total_actions={TurnAction.LIKE: 5},
            created_at="2024_01_01-12:00:00",
        )
        adapter_error = DuplicateTurnMetadataError(run_id, 0)
        mock_adapter.write_turn_metadata.side_effect = adapter_error

        # Act & Assert
        with pytest.raises(DuplicateTurnMetadataError) as exc_info:
            repo.write_turn_metadata(turn_metadata)

        assert exc_info.value.run_id == run_id
        assert exc_info.value.turn_number == 0
        mock_adapter.write_turn_metadata.assert_called_once_with(turn_metadata)

    def test_propagates_database_exceptions(self):
        """Test that write_turn_metadata propagates database exceptions from adapter."""
        # Arrange
        import sqlite3

        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-12:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        run_id = "run_123"

        # Mock get_run to return a proper Run object
        mock_run = Run(
            run_id=run_id,
            created_at="2024_01_01-12:00:00",
            total_turns=5,
            total_agents=3,
            started_at="2024_01_01-12:00:00",
            status=RunStatus.RUNNING,
            completed_at=None,
        )
        repo.get_run = Mock(return_value=mock_run)

        turn_metadata = TurnMetadata(
            run_id=run_id,
            turn_number=0,
            total_actions={TurnAction.LIKE: 5},
            created_at="2024_01_01-12:00:00",
        )
        adapter_error = sqlite3.OperationalError("Database locked")
        mock_adapter.write_turn_metadata.side_effect = adapter_error

        # Act & Assert
        with pytest.raises(sqlite3.OperationalError, match="Database locked"):
            repo.write_turn_metadata(turn_metadata)

        mock_adapter.write_turn_metadata.assert_called_once_with(turn_metadata)

    def test_calls_adapter_with_correct_turn_metadata(self):
        """Test that write_turn_metadata calls adapter with correct TurnMetadata object."""
        # Arrange
        mock_adapter = Mock(spec=RunDatabaseAdapter)
        mock_get_timestamp = Mock(return_value="2024_01_01-12:00:00")
        repo = SQLiteRunRepository(mock_adapter, mock_get_timestamp)
        run_id = "run_123"

        # Mock get_run to return a proper Run object with enough turns
        mock_run = Run(
            run_id=run_id,
            created_at="2024_01_01-12:00:00",
            total_turns=10,  # Enough turns to allow turn_number=5
            total_agents=3,
            started_at="2024_01_01-12:00:00",
            status=RunStatus.RUNNING,
            completed_at=None,
        )
        repo.get_run = Mock(return_value=mock_run)

        turn_metadata = TurnMetadata(
            run_id=run_id,
            turn_number=5,
            total_actions={
                TurnAction.LIKE: 10,
                TurnAction.COMMENT: 5,
                TurnAction.FOLLOW: 3,
            },
            created_at="2024_01_01-12:00:00",
        )

        # Act
        repo.write_turn_metadata(turn_metadata)

        # Assert
        mock_adapter.write_turn_metadata.assert_called_once_with(turn_metadata)
        # Verify the exact object passed
        call_args = mock_adapter.write_turn_metadata.call_args[0]
        assert len(call_args) == 1
        assert call_args[0] == turn_metadata
