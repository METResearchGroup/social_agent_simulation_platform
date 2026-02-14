"""Integration tests for db.repositories.run_repository module.

These tests use a real SQLite database to test end-to-end functionality.
"""

import os
import tempfile
import time

import pytest

from db.adapters.sqlite.sqlite import DB_PATH, get_connection, initialize_database
from db.exceptions import (
    DuplicateTurnMetadataError,
    InvalidTransitionError,
    RunNotFoundError,
)
from db.repositories.run_repository import create_sqlite_repository
from simulation.core.models.runs import Run, RunConfig, RunStatus


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    # Save original DB path
    original_path = DB_PATH

    # Create temporary database
    fd, temp_path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)

    # Monkey-patch DB_PATH
    import db.adapters.sqlite.sqlite as sqlite_module

    sqlite_module.DB_PATH = temp_path

    # Initialize the database
    initialize_database()

    yield temp_path

    # Cleanup
    sqlite_module.DB_PATH = original_path
    if os.path.exists(temp_path):
        os.unlink(temp_path)


class TestSQLiteRunRepositoryIntegration:
    """Integration tests using a real database."""

    def test_create_and_read_run(self, temp_db):
        """Test creating a run and reading it back from the database."""
        repo = create_sqlite_repository()
        config = RunConfig(num_agents=5, num_turns=10, feed_algorithm="chronological")

        # Create run
        created_run = repo.create_run(config)
        assert created_run.status == RunStatus.RUNNING
        assert created_run.total_agents == 5
        assert created_run.total_turns == 10

        # Read it back
        retrieved_run = repo.get_run(created_run.run_id)
        assert retrieved_run is not None
        assert retrieved_run.run_id == created_run.run_id
        assert retrieved_run.status == RunStatus.RUNNING
        assert retrieved_run.total_agents == 5
        assert retrieved_run.total_turns == 10

    def test_update_run_status_to_completed(self, temp_db):
        """Test updating run status to completed."""
        repo = create_sqlite_repository()
        config = RunConfig(num_agents=3, num_turns=5, feed_algorithm="chronological")

        run = repo.create_run(config)

        # Update to completed
        repo.update_run_status(run.run_id, RunStatus.COMPLETED)

        # Verify update
        updated_run = repo.get_run(run.run_id)
        assert updated_run is not None
        assert updated_run.status == RunStatus.COMPLETED
        assert updated_run.completed_at is not None

    def test_update_run_status_to_failed(self, temp_db):
        """Test updating run status to failed."""
        repo = create_sqlite_repository()
        config = RunConfig(num_agents=3, num_turns=5, feed_algorithm="chronological")

        run = repo.create_run(config)

        # Update to failed
        repo.update_run_status(run.run_id, RunStatus.FAILED)

        # Verify update
        updated_run = repo.get_run(run.run_id)
        assert updated_run is not None
        assert updated_run.status == RunStatus.FAILED
        assert updated_run.completed_at is None

    def test_update_run_status_nonexistent_run(self, temp_db):
        """Test updating status of a non-existent run raises error."""
        repo = create_sqlite_repository()

        with pytest.raises(RunNotFoundError) as exc_info:
            repo.update_run_status("nonexistent_run_id", RunStatus.COMPLETED)

        assert exc_info.value.run_id == "nonexistent_run_id"

    def test_list_runs_returns_all_runs_ordered(self, temp_db):
        """Test that list_runs returns all runs in correct order."""
        repo = create_sqlite_repository()

        # Create multiple runs with delays to ensure distinct timestamps
        run1 = repo.create_run(
            RunConfig(num_agents=1, num_turns=1, feed_algorithm="chronological")
        )
        time.sleep(1.1)  # Ensure different timestamp (format is down to seconds)
        run2 = repo.create_run(
            RunConfig(num_agents=2, num_turns=2, feed_algorithm="chronological")
        )
        time.sleep(1.1)
        run3 = repo.create_run(
            RunConfig(num_agents=3, num_turns=3, feed_algorithm="chronological")
        )

        # List runs (should be ordered by created_at DESC, so newest first)
        runs = repo.list_runs()

        assert len(runs) >= 3
        # Verify ordering (newest first)
        run_ids = [r.run_id for r in runs[:3]]
        expected_order = [run3.run_id, run2.run_id, run1.run_id]
        assert run_ids == expected_order


class TestRunStatusEnumSerialization:
    """Tests for RunStatus enum serialization/deserialization."""

    def test_enum_serializes_to_correct_string(self, temp_db):
        """Test that RunStatus enum values serialize correctly."""
        from db.adapters.sqlite.run_adapter import SQLiteRunAdapter

        adapter = SQLiteRunAdapter()

        run = Run(
            run_id="test_run_1",
            created_at="2024_01_01-12:00:00",
            total_turns=5,
            total_agents=3,
            started_at="2024_01_01-12:00:00",
            status=RunStatus.RUNNING,
            completed_at=None,
        )

        adapter.write_run(run)

        # Read directly from DB to verify string storage
        conn = get_connection()
        row = conn.execute(
            "SELECT status FROM runs WHERE run_id = ?", (run.run_id,)
        ).fetchone()
        assert row["status"] == "running"
        conn.close()

    def test_invalid_status_string_raises_error(self, temp_db):
        """Test that reading invalid status string raises ValueError."""
        from unittest.mock import MagicMock

        from db.adapters.sqlite.run_adapter import SQLiteRunAdapter

        adapter = SQLiteRunAdapter()

        # We can't insert invalid status due to CHECK constraint, so we test _row_to_run directly
        # This simulates what would happen if the database had invalid data (e.g., from manual edits)

        # Create a mock row that simulates invalid status
        mock_row = MagicMock()

        def getitem(key):
            mapping = {
                "run_id": "test_run",
                "created_at": "2024_01_01-12:00:00",
                "total_turns": 5,
                "total_agents": 3,
                "started_at": "2024_01_01-12:00:00",
                "status": "invalid_status",  # Invalid status value
                "completed_at": None,
            }
            return mapping.get(key)

        # Configure mock to work with row[key] syntax
        type(mock_row).__getitem__ = lambda self, key: getitem(key)
        mock_row.keys = lambda: [
            "run_id",
            "created_at",
            "total_turns",
            "total_agents",
            "started_at",
            "status",
            "completed_at",
        ]

        # Test that _row_to_run raises ValueError for invalid status
        with pytest.raises(ValueError, match="Invalid status value"):
            adapter._row_to_run(mock_row)

    def test_all_status_values_roundtrip(self, temp_db):
        """Test that all RunStatus enum values roundtrip correctly."""
        repo = create_sqlite_repository()
        config = RunConfig(num_agents=2, num_turns=2, feed_algorithm="chronological")

        # Test RUNNING status (default from create_run)
        run_running = repo.create_run(config)
        retrieved = repo.get_run(run_running.run_id)
        assert retrieved is not None
        assert retrieved.status == RunStatus.RUNNING

        # Test COMPLETED status (valid transition from RUNNING)
        run_completed = repo.create_run(config)
        repo.update_run_status(run_completed.run_id, RunStatus.COMPLETED)
        retrieved = repo.get_run(run_completed.run_id)
        assert retrieved is not None
        assert retrieved.status == RunStatus.COMPLETED

        # Test FAILED status (valid transition from RUNNING)
        run_failed = repo.create_run(config)
        repo.update_run_status(run_failed.run_id, RunStatus.FAILED)
        retrieved = repo.get_run(run_failed.run_id)
        assert retrieved is not None
        assert retrieved.status == RunStatus.FAILED

        # Test idempotent updates (setting same status again)
        repo.update_run_status(run_completed.run_id, RunStatus.COMPLETED)
        retrieved = repo.get_run(run_completed.run_id)
        assert retrieved is not None
        assert retrieved.status == RunStatus.COMPLETED

        repo.update_run_status(run_failed.run_id, RunStatus.FAILED)
        retrieved = repo.get_run(run_failed.run_id)
        assert retrieved is not None
        assert retrieved.status == RunStatus.FAILED


class TestConcurrentRunCreation:
    """Tests for concurrent run creation scenarios."""

    def test_concurrent_run_creation_generates_unique_ids(self, temp_db):
        """Test that concurrent run creation generates unique run IDs."""
        import threading

        repo = create_sqlite_repository()
        config = RunConfig(num_agents=1, num_turns=1, feed_algorithm="chronological")

        run_ids = []
        errors = []

        def create_run():
            try:
                run = repo.create_run(config)
                run_ids.append(run.run_id)
            except Exception as e:
                errors.append(e)

        # Create runs concurrently
        threads = [threading.Thread(target=create_run) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Verify all succeeded
        assert len(errors) == 0
        assert len(run_ids) == 10

        # Verify all IDs are unique
        assert len(set(run_ids)) == 10


class TestStateMachineValidationIntegration:
    """Integration tests for state machine validation."""

    def test_valid_transition_running_to_completed(self, temp_db):
        """Test that RUNNING -> COMPLETED transition works with real database."""
        repo = create_sqlite_repository()
        config = RunConfig(num_agents=3, num_turns=5, feed_algorithm="chronological")

        run = repo.create_run(config)
        assert run.status == RunStatus.RUNNING

        # Transition to completed
        repo.update_run_status(run.run_id, RunStatus.COMPLETED)

        updated_run = repo.get_run(run.run_id)
        assert updated_run is not None
        assert updated_run.status == RunStatus.COMPLETED

    def test_valid_transition_running_to_failed(self, temp_db):
        """Test that RUNNING -> FAILED transition works with real database."""
        repo = create_sqlite_repository()
        config = RunConfig(num_agents=3, num_turns=5, feed_algorithm="chronological")

        run = repo.create_run(config)
        assert run.status == RunStatus.RUNNING

        # Transition to failed
        repo.update_run_status(run.run_id, RunStatus.FAILED)

        updated_run = repo.get_run(run.run_id)
        assert updated_run is not None
        assert updated_run.status == RunStatus.FAILED

    def test_invalid_transition_completed_to_failed(self, temp_db):
        """Test that COMPLETED -> FAILED transition is rejected."""
        repo = create_sqlite_repository()
        config = RunConfig(num_agents=3, num_turns=5, feed_algorithm="chronological")

        run = repo.create_run(config)
        repo.update_run_status(run.run_id, RunStatus.COMPLETED)

        # Try invalid transition
        with pytest.raises(InvalidTransitionError) as exc_info:
            repo.update_run_status(run.run_id, RunStatus.FAILED)

        assert exc_info.value.run_id == run.run_id
        assert exc_info.value.current_status == "completed"
        assert exc_info.value.target_status == "failed"

        # Verify status is still COMPLETED
        updated_run = repo.get_run(run.run_id)
        assert updated_run is not None
        assert updated_run.status == RunStatus.COMPLETED

    def test_invalid_transition_failed_to_completed(self, temp_db):
        """Test that FAILED -> COMPLETED transition is rejected."""
        repo = create_sqlite_repository()
        config = RunConfig(num_agents=3, num_turns=5, feed_algorithm="chronological")

        run = repo.create_run(config)
        repo.update_run_status(run.run_id, RunStatus.FAILED)

        # Try invalid transition
        with pytest.raises(InvalidTransitionError) as exc_info:
            repo.update_run_status(run.run_id, RunStatus.COMPLETED)

        assert exc_info.value.run_id == run.run_id
        assert exc_info.value.current_status == "failed"
        assert exc_info.value.target_status == "completed"

        # Verify status is still FAILED
        updated_run = repo.get_run(run.run_id)
        assert updated_run is not None
        assert updated_run.status == RunStatus.FAILED

    def test_invalid_transition_completed_to_running(self, temp_db):
        """Test that COMPLETED -> RUNNING transition is rejected."""
        repo = create_sqlite_repository()
        config = RunConfig(num_agents=3, num_turns=5, feed_algorithm="chronological")

        run = repo.create_run(config)
        repo.update_run_status(run.run_id, RunStatus.COMPLETED)

        # Try invalid transition
        with pytest.raises(InvalidTransitionError) as exc_info:
            repo.update_run_status(run.run_id, RunStatus.RUNNING)

        assert exc_info.value.run_id == run.run_id
        assert exc_info.value.current_status == "completed"
        assert exc_info.value.target_status == "running"

        # Verify status is still COMPLETED
        updated_run = repo.get_run(run.run_id)
        assert updated_run is not None
        assert updated_run.status == RunStatus.COMPLETED

    def test_idempotent_status_update_completed(self, temp_db):
        """Test that setting COMPLETED status again is allowed (idempotent)."""
        repo = create_sqlite_repository()
        config = RunConfig(num_agents=3, num_turns=5, feed_algorithm="chronological")

        run = repo.create_run(config)
        repo.update_run_status(run.run_id, RunStatus.COMPLETED)

        # Setting to COMPLETED again should work
        repo.update_run_status(run.run_id, RunStatus.COMPLETED)

        updated_run = repo.get_run(run.run_id)
        assert updated_run is not None
        assert updated_run.status == RunStatus.COMPLETED

    def test_idempotent_status_update_failed(self, temp_db):
        """Test that setting FAILED status again is allowed (idempotent)."""
        repo = create_sqlite_repository()
        config = RunConfig(num_agents=3, num_turns=5, feed_algorithm="chronological")

        run = repo.create_run(config)
        repo.update_run_status(run.run_id, RunStatus.FAILED)

        # Setting to FAILED again should work
        repo.update_run_status(run.run_id, RunStatus.FAILED)

        updated_run = repo.get_run(run.run_id)
        assert updated_run is not None
        assert updated_run.status == RunStatus.FAILED


def _create_mock_row(**overrides):
    """Helper function to create a MockRow that mimics sqlite3.Row behavior.

    Args:
        **overrides: Dictionary of field overrides to apply to default values.

    Returns:
        MockRow instance with __getitem__ and keys methods.
    """
    default_data = {
        "run_id": "test_run",
        "created_at": "2024_01_01-12:00:00",
        "total_turns": 5,
        "total_agents": 3,
        "started_at": "2024_01_01-12:00:00",
        "status": "running",
        "completed_at": None,
    }
    default_data.update(overrides)

    class MockRow:
        def __init__(self, data):
            self._data = data

        def __getitem__(self, key):
            return self._data[key]

        def keys(self):
            return list(self._data.keys())

    return MockRow(default_data)


class TestNullabilityValidation:
    """Tests for nullability validation when reading runs."""

    def test_null_run_id_raises_error(self, temp_db):
        """Test that NULL run_id raises ValueError."""
        from db.adapters.sqlite.run_adapter import SQLiteRunAdapter

        adapter = SQLiteRunAdapter()
        mock_row = _create_mock_row(run_id=None)

        with pytest.raises(ValueError, match="run_id cannot be NULL"):
            adapter._row_to_run(mock_row)  # type: ignore

    def test_null_status_raises_error(self, temp_db):
        """Test that NULL status raises ValueError."""
        from db.adapters.sqlite.run_adapter import SQLiteRunAdapter

        adapter = SQLiteRunAdapter()
        mock_row = _create_mock_row(status=None)

        with pytest.raises(ValueError, match="status cannot be NULL"):
            adapter._row_to_run(mock_row)  # type: ignore


class TestTurnMetadataIntegration:
    """Integration tests for turn metadata operations."""

    def test_write_and_read_turn_metadata(self, temp_db):
        """Test writing turn metadata using repository and reading it back."""
        from lib.timestamp_utils import get_current_timestamp
        from simulation.core.models.actions import TurnAction
        from simulation.core.models.turns import TurnMetadata

        # Create a run first
        repo = create_sqlite_repository()
        config = RunConfig(num_agents=3, num_turns=5, feed_algorithm="chronological")
        run = repo.create_run(config)

        # Write turn metadata using repository
        turn_number = 0
        turn_metadata = TurnMetadata(
            run_id=run.run_id,
            turn_number=turn_number,
            total_actions={
                TurnAction.LIKE: 5,
                TurnAction.COMMENT: 2,
                TurnAction.FOLLOW: 1,
            },
            created_at=get_current_timestamp(),
        )
        repo.write_turn_metadata(turn_metadata)

        # Read it back via repository
        result = repo.get_turn_metadata(run.run_id, turn_number)

        # Assert
        assert result is not None
        assert result.run_id == run.run_id
        assert result.turn_number == turn_number
        assert result.total_actions[TurnAction.LIKE] == 5
        assert result.total_actions[TurnAction.COMMENT] == 2
        assert result.total_actions[TurnAction.FOLLOW] == 1
        assert result.created_at == turn_metadata.created_at

    def test_read_turn_metadata_returns_none_when_not_found(self, temp_db):
        """Test that get_turn_metadata returns None when metadata doesn't exist."""
        repo = create_sqlite_repository()
        config = RunConfig(num_agents=3, num_turns=5, feed_algorithm="chronological")
        run = repo.create_run(config)

        # Try to read non-existent turn metadata
        result = repo.get_turn_metadata(run.run_id, turn_number=999)

        # Assert
        assert result is None

    def test_read_turn_metadata_with_multiple_turns(self, temp_db):
        """Test reading turn metadata for multiple turns in the same run."""
        from simulation.core.models.actions import TurnAction

        # Create a run
        repo = create_sqlite_repository()
        config = RunConfig(num_agents=3, num_turns=5, feed_algorithm="chronological")
        run = repo.create_run(config)

        # Write metadata for multiple turns
        import json

        from db.adapters.sqlite.sqlite import get_connection

        with get_connection() as conn:
            for turn_number in range(3):
                total_actions = {
                    TurnAction.LIKE: turn_number * 2,
                    TurnAction.COMMENT: turn_number,
                    TurnAction.FOLLOW: turn_number * 3,
                }
                total_actions_json = json.dumps(
                    {k.value: v for k, v in total_actions.items()}
                )
                conn.execute(
                    """
                    INSERT INTO turn_metadata (run_id, turn_number, total_actions, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        run.run_id,
                        turn_number,
                        total_actions_json,
                        "2024_01_01-12:00:00",
                    ),
                )
            conn.commit()

        # Read each turn's metadata
        for turn_number in range(3):
            result = repo.get_turn_metadata(run.run_id, turn_number)
            assert result is not None
            assert result.turn_number == turn_number
            assert result.total_actions[TurnAction.LIKE] == turn_number * 2
            assert result.total_actions[TurnAction.COMMENT] == turn_number
            assert result.total_actions[TurnAction.FOLLOW] == turn_number * 3

    def test_read_turn_metadata_with_zero_actions(self, temp_db):
        """Test reading turn metadata with all actions set to zero."""
        from simulation.core.models.actions import TurnAction

        # Create a run
        repo = create_sqlite_repository()
        config = RunConfig(num_agents=3, num_turns=5, feed_algorithm="chronological")
        run = repo.create_run(config)

        # Write metadata with zero actions
        import json

        from db.adapters.sqlite.sqlite import get_connection

        turn_number = 0
        total_actions = {
            TurnAction.LIKE: 0,
            TurnAction.COMMENT: 0,
            TurnAction.FOLLOW: 0,
        }
        total_actions_json = json.dumps({k.value: v for k, v in total_actions.items()})

        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO turn_metadata (run_id, turn_number, total_actions, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (run.run_id, turn_number, total_actions_json, "2024_01_01-12:00:00"),
            )
            conn.commit()

        # Read it back
        result = repo.get_turn_metadata(run.run_id, turn_number)

        # Assert
        assert result is not None
        assert result.total_actions[TurnAction.LIKE] == 0
        assert result.total_actions[TurnAction.COMMENT] == 0
        assert result.total_actions[TurnAction.FOLLOW] == 0

    def test_read_turn_metadata_different_runs(self, temp_db):
        """Test that turn metadata is correctly isolated per run."""
        from simulation.core.models.actions import TurnAction

        # Create two runs
        repo = create_sqlite_repository()
        run1 = repo.create_run(
            RunConfig(num_agents=2, num_turns=3, feed_algorithm="chronological")
        )
        run2 = repo.create_run(
            RunConfig(num_agents=2, num_turns=3, feed_algorithm="chronological")
        )

        # Write metadata for turn 0 in both runs with different values
        import json

        from db.adapters.sqlite.sqlite import get_connection

        with get_connection() as conn:
            # Run 1: turn 0 has 10 likes
            total_actions_1 = {
                TurnAction.LIKE: 10,
                TurnAction.COMMENT: 0,
                TurnAction.FOLLOW: 0,
            }
            total_actions_json_1 = json.dumps(
                {k.value: v for k, v in total_actions_1.items()}
            )
            conn.execute(
                """
                INSERT INTO turn_metadata (run_id, turn_number, total_actions, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (run1.run_id, 0, total_actions_json_1, "2024_01_01-12:00:00"),
            )

            # Run 2: turn 0 has 20 likes
            total_actions_2 = {
                TurnAction.LIKE: 20,
                TurnAction.COMMENT: 0,
                TurnAction.FOLLOW: 0,
            }
            total_actions_json_2 = json.dumps(
                {k.value: v for k, v in total_actions_2.items()}
            )
            conn.execute(
                """
                INSERT INTO turn_metadata (run_id, turn_number, total_actions, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (run2.run_id, 0, total_actions_json_2, "2024_01_01-12:00:00"),
            )
            conn.commit()

        # Read both and verify they're different
        result1 = repo.get_turn_metadata(run1.run_id, 0)
        result2 = repo.get_turn_metadata(run2.run_id, 0)

        assert result1 is not None
        assert result2 is not None
        assert result1.total_actions[TurnAction.LIKE] == 10
        assert result2.total_actions[TurnAction.LIKE] == 20

    def test_write_turn_metadata_using_repository_method(self, temp_db):
        """Test writing turn metadata using repository.write_turn_metadata method."""
        from lib.timestamp_utils import get_current_timestamp
        from simulation.core.models.actions import TurnAction
        from simulation.core.models.turns import TurnMetadata

        # Create a run
        repo = create_sqlite_repository()
        config = RunConfig(num_agents=3, num_turns=5, feed_algorithm="chronological")
        run = repo.create_run(config)

        # Write turn metadata using repository method
        turn_metadata = TurnMetadata(
            run_id=run.run_id,
            turn_number=0,
            total_actions={
                TurnAction.LIKE: 10,
                TurnAction.COMMENT: 5,
                TurnAction.FOLLOW: 3,
            },
            created_at=get_current_timestamp(),
        )
        repo.write_turn_metadata(turn_metadata)

        # Read it back
        result = repo.get_turn_metadata(run.run_id, 0)

        # Assert
        assert result is not None
        assert result.run_id == run.run_id
        assert result.turn_number == 0
        assert result.total_actions[TurnAction.LIKE] == 10
        assert result.total_actions[TurnAction.COMMENT] == 5
        assert result.total_actions[TurnAction.FOLLOW] == 3
        assert result.created_at == turn_metadata.created_at

    def test_write_multiple_turns_using_repository_method(self, temp_db):
        """Test writing multiple turns using repository.write_turn_metadata method."""
        from lib.timestamp_utils import get_current_timestamp
        from simulation.core.models.actions import TurnAction
        from simulation.core.models.turns import TurnMetadata

        # Create a run
        repo = create_sqlite_repository()
        config = RunConfig(num_agents=3, num_turns=5, feed_algorithm="chronological")
        run = repo.create_run(config)

        # Write metadata for multiple turns
        for turn_number in range(3):
            turn_metadata = TurnMetadata(
                run_id=run.run_id,
                turn_number=turn_number,
                total_actions={
                    TurnAction.LIKE: turn_number * 2,
                    TurnAction.COMMENT: turn_number,
                    TurnAction.FOLLOW: turn_number * 3,
                },
                created_at=get_current_timestamp(),
            )
            repo.write_turn_metadata(turn_metadata)

        # Read each turn's metadata
        for turn_number in range(3):
            result = repo.get_turn_metadata(run.run_id, turn_number)
            assert result is not None
            assert result.turn_number == turn_number
            assert result.total_actions[TurnAction.LIKE] == turn_number * 2
            assert result.total_actions[TurnAction.COMMENT] == turn_number
            assert result.total_actions[TurnAction.FOLLOW] == turn_number * 3

    def test_write_turn_metadata_with_zero_actions_using_repository(self, temp_db):
        """Test writing turn metadata with zero actions using repository method."""
        from lib.timestamp_utils import get_current_timestamp
        from simulation.core.models.actions import TurnAction
        from simulation.core.models.turns import TurnMetadata

        # Create a run
        repo = create_sqlite_repository()
        config = RunConfig(num_agents=3, num_turns=5, feed_algorithm="chronological")
        run = repo.create_run(config)

        # Write metadata with zero actions
        turn_metadata = TurnMetadata(
            run_id=run.run_id,
            turn_number=0,
            total_actions={
                TurnAction.LIKE: 0,
                TurnAction.COMMENT: 0,
                TurnAction.FOLLOW: 0,
            },
            created_at=get_current_timestamp(),
        )
        repo.write_turn_metadata(turn_metadata)

        # Read it back
        result = repo.get_turn_metadata(run.run_id, 0)

        # Assert
        assert result is not None
        assert result.total_actions[TurnAction.LIKE] == 0
        assert result.total_actions[TurnAction.COMMENT] == 0
        assert result.total_actions[TurnAction.FOLLOW] == 0

    def test_write_turn_metadata_different_runs_using_repository(self, temp_db):
        """Test that turn metadata is correctly isolated per run using repository method."""
        from lib.timestamp_utils import get_current_timestamp
        from simulation.core.models.actions import TurnAction
        from simulation.core.models.turns import TurnMetadata

        # Create two runs
        repo = create_sqlite_repository()
        run1 = repo.create_run(
            RunConfig(num_agents=2, num_turns=3, feed_algorithm="chronological")
        )
        run2 = repo.create_run(
            RunConfig(num_agents=2, num_turns=3, feed_algorithm="chronological")
        )

        # Write metadata for turn 0 in both runs with different values
        turn_metadata_1 = TurnMetadata(
            run_id=run1.run_id,
            turn_number=0,
            total_actions={
                TurnAction.LIKE: 10,
                TurnAction.COMMENT: 0,
                TurnAction.FOLLOW: 0,
            },
            created_at=get_current_timestamp(),
        )
        repo.write_turn_metadata(turn_metadata_1)

        turn_metadata_2 = TurnMetadata(
            run_id=run2.run_id,
            turn_number=0,
            total_actions={
                TurnAction.LIKE: 20,
                TurnAction.COMMENT: 0,
                TurnAction.FOLLOW: 0,
            },
            created_at=get_current_timestamp(),
        )
        repo.write_turn_metadata(turn_metadata_2)

        # Read both and verify they're different
        result1 = repo.get_turn_metadata(run1.run_id, 0)
        result2 = repo.get_turn_metadata(run2.run_id, 0)

        assert result1 is not None
        assert result2 is not None
        assert result1.total_actions[TurnAction.LIKE] == 10
        assert result2.total_actions[TurnAction.LIKE] == 20

    def test_write_turn_metadata_raises_duplicate_error(self, temp_db):
        """Test that writing duplicate turn metadata raises DuplicateTurnMetadataError."""
        from lib.timestamp_utils import get_current_timestamp
        from simulation.core.models.actions import TurnAction
        from simulation.core.models.turns import TurnMetadata

        # Create a run
        repo = create_sqlite_repository()
        config = RunConfig(num_agents=3, num_turns=5, feed_algorithm="chronological")
        run = repo.create_run(config)

        # Write turn metadata once
        turn_metadata = TurnMetadata(
            run_id=run.run_id,
            turn_number=0,
            total_actions={TurnAction.LIKE: 5},
            created_at=get_current_timestamp(),
        )
        repo.write_turn_metadata(turn_metadata)

        # Try to write the same metadata again
        with pytest.raises(DuplicateTurnMetadataError) as exc_info:
            repo.write_turn_metadata(turn_metadata)

        assert exc_info.value.run_id == run.run_id
        assert exc_info.value.turn_number == 0

    def test_write_turn_metadata_raises_error_when_run_not_found(self, temp_db):
        """Test that writing turn metadata for non-existent run raises RunNotFoundError."""
        from lib.timestamp_utils import get_current_timestamp
        from simulation.core.models.actions import TurnAction
        from simulation.core.models.turns import TurnMetadata

        repo = create_sqlite_repository()

        # Try to write metadata for a non-existent run
        turn_metadata = TurnMetadata(
            run_id="nonexistent_run",
            turn_number=0,
            total_actions={TurnAction.LIKE: 5},
            created_at=get_current_timestamp(),
        )

        with pytest.raises(RunNotFoundError) as exc_info:
            repo.write_turn_metadata(turn_metadata)

        assert exc_info.value.run_id == "nonexistent_run"

    def test_write_turn_metadata_raises_error_when_turn_number_out_of_bounds(
        self, temp_db
    ):
        """Test that writing turn metadata with out-of-bounds turn_number raises ValueError."""
        from lib.timestamp_utils import get_current_timestamp
        from simulation.core.models.actions import TurnAction
        from simulation.core.models.turns import TurnMetadata

        # Create a run with 5 turns (0-4)
        repo = create_sqlite_repository()
        config = RunConfig(num_agents=3, num_turns=5, feed_algorithm="chronological")
        run = repo.create_run(config)

        # Try to write metadata for turn 5 (out of bounds)
        turn_metadata = TurnMetadata(
            run_id=run.run_id,
            turn_number=5,  # Out of bounds (should be 0-4)
            total_actions={TurnAction.LIKE: 5},
            created_at=get_current_timestamp(),
        )

        with pytest.raises(
            ValueError,
            match="Turn number 5 is greater than the maximum number of turns: 5",
        ):
            repo.write_turn_metadata(turn_metadata)
