"""Tests for db.adapters.sqlite.run_adapter module."""

import json
import sqlite3
from unittest.mock import Mock

import pytest

from db.adapters.sqlite.run_adapter import SQLiteRunAdapter
from simulation.core.models.actions import TurnAction
from simulation.core.models.turns import TurnMetadata
from tests.db.adapters.sqlite.conftest import create_mock_row
from tests.factories import TurnMetadataFactory


@pytest.fixture
def adapter():
    """Create a SQLiteRunAdapter instance."""
    return SQLiteRunAdapter()


@pytest.fixture
def default_test_data():
    """Common test data used across multiple tests."""
    return {"run_id": "run_123", "turn_number": 0}


class TestSQLiteRunAdapterReadTurnMetadata:
    """Tests for SQLiteRunAdapter.read_turn_metadata method."""

    def test_returns_turn_metadata_when_found(
        self, adapter, default_test_data, mock_db_connection
    ):
        """Test that read_turn_metadata returns TurnMetadata when row exists."""
        # Arrange
        run_id = default_test_data["run_id"]
        turn_number = default_test_data["turn_number"]
        # JSON stores enum values as strings
        total_actions_json = json.dumps({"like": 5, "comment": 2, "follow": 1})

        row_data = {
            "run_id": run_id,
            "turn_number": turn_number,
            "total_actions": total_actions_json,
            "created_at": "2024_01_01-12:00:00",
        }
        mock_row = create_mock_row(row_data)

        with mock_db_connection() as (mock_conn, mock_cursor):
            mock_cursor.fetchone.return_value = mock_row

            # Act
            result = adapter.read_turn_metadata(run_id, turn_number, conn=mock_conn)

            # Assert
            assert result is not None
            assert isinstance(result, TurnMetadata)
            assert result.run_id == run_id
            assert result.turn_number == turn_number
            assert result.created_at == "2024_01_01-12:00:00"
            # Adapter explicitly converts string keys to TurnAction enum keys
            assert result.total_actions[TurnAction.LIKE] == 5
            assert result.total_actions[TurnAction.COMMENT] == 2
            assert result.total_actions[TurnAction.FOLLOW] == 1

    def test_returns_none_when_not_found(
        self, adapter, default_test_data, mock_db_connection
    ):
        """Test that read_turn_metadata returns None when row doesn't exist."""
        # Arrange
        run_id = default_test_data["run_id"]
        turn_number = default_test_data["turn_number"]

        with mock_db_connection() as (mock_conn, mock_cursor):
            mock_cursor.fetchone.return_value = None

            # Act
            result = adapter.read_turn_metadata(run_id, turn_number, conn=mock_conn)

            # Assert
            assert result is None

    def test_raises_operational_error_on_database_error(
        self, adapter, default_test_data, mock_db_connection
    ):
        """Test that read_turn_metadata raises OperationalError on database errors."""
        # Arrange
        run_id = default_test_data["run_id"]
        turn_number = default_test_data["turn_number"]
        db_error = sqlite3.OperationalError("Database locked")

        with mock_db_connection() as (mock_conn, mock_cursor):
            mock_conn.execute.side_effect = db_error

            # Act & Assert
            with pytest.raises(sqlite3.OperationalError):
                adapter.read_turn_metadata(run_id, turn_number, conn=mock_conn)

    def test_raises_keyerror_when_missing_required_column(
        self, adapter, default_test_data, mock_db_connection
    ):
        """Test that read_turn_metadata raises KeyError when required column is missing."""
        # Arrange
        run_id = default_test_data["run_id"]
        turn_number = default_test_data["turn_number"]

        # Create a mock row missing the 'total_actions' column
        row_data = {
            "run_id": run_id,
            "turn_number": turn_number,
            # Missing "total_actions"
            "created_at": "2024_01_01-12:00:00",
        }
        mock_row = create_mock_row(row_data)

        with mock_db_connection() as (mock_conn, mock_cursor):
            mock_cursor.fetchone.return_value = mock_row

            # Act & Assert
            with pytest.raises(
                KeyError, match="Missing required column 'total_actions'"
            ):
                adapter.read_turn_metadata(run_id, turn_number, conn=mock_conn)

    def test_raises_keyerror_when_missing_created_at_column(
        self, adapter, default_test_data, mock_db_connection
    ):
        """Test that read_turn_metadata raises KeyError when created_at column is missing."""
        # Arrange
        run_id = default_test_data["run_id"]
        turn_number = default_test_data["turn_number"]

        # Create a mock row missing the 'created_at' column
        row_data = {
            "run_id": run_id,
            "turn_number": turn_number,
            "total_actions": '{"like": 5}',
            # Missing "created_at"
        }
        mock_row = create_mock_row(row_data)

        with mock_db_connection() as (mock_conn, mock_cursor):
            mock_cursor.fetchone.return_value = mock_row

            # Act & Assert
            with pytest.raises(KeyError, match="Missing required column 'created_at'"):
                adapter.read_turn_metadata(run_id, turn_number, conn=mock_conn)

    def test_raises_valueerror_when_null_fields(
        self, adapter, default_test_data, mock_db_connection
    ):
        """Test that read_turn_metadata raises ValueError when fields are NULL."""
        # Arrange
        run_id = default_test_data["run_id"]
        turn_number = default_test_data["turn_number"]

        # Create a mock row with NULL turn_number
        row_data = {
            "run_id": run_id,
            "turn_number": None,  # NULL
            "total_actions": '{"like": 5}',
            "created_at": "2024_01_01-12:00:00",
        }
        mock_row = create_mock_row(row_data)

        with mock_db_connection() as (mock_conn, mock_cursor):
            mock_cursor.fetchone.return_value = mock_row

            # Act & Assert
            with pytest.raises(ValueError, match="Turn metadata has NULL fields"):
                adapter.read_turn_metadata(run_id, turn_number, conn=mock_conn)

    def test_raises_valueerror_when_null_created_at(
        self, adapter, default_test_data, mock_db_connection
    ):
        """Test that read_turn_metadata raises ValueError when created_at is NULL."""
        # Arrange
        run_id = default_test_data["run_id"]
        turn_number = default_test_data["turn_number"]

        # Create a mock row with NULL created_at
        row_data = {
            "run_id": run_id,
            "turn_number": turn_number,
            "total_actions": '{"like": 5}',
            "created_at": None,  # NULL
        }
        mock_row = create_mock_row(row_data)

        with mock_db_connection() as (mock_conn, mock_cursor):
            mock_cursor.fetchone.return_value = mock_row

            # Act & Assert
            with pytest.raises(ValueError, match="Turn metadata has NULL fields"):
                adapter.read_turn_metadata(run_id, turn_number, conn=mock_conn)

    def test_raises_valueerror_when_invalid_json(
        self, adapter, default_test_data, mock_db_connection
    ):
        """Test that read_turn_metadata raises ValueError when total_actions is invalid JSON."""
        # Arrange
        run_id = default_test_data["run_id"]
        turn_number = default_test_data["turn_number"]

        # Create a mock row with invalid JSON
        row_data = {
            "run_id": run_id,
            "turn_number": turn_number,
            "total_actions": "not valid json{",
            "created_at": "2024_01_01-12:00:00",
        }
        mock_row = create_mock_row(row_data)

        with mock_db_connection() as (mock_conn, mock_cursor):
            mock_cursor.fetchone.return_value = mock_row

            # Act & Assert
            with pytest.raises(
                ValueError, match="Could not parse total_actions as JSON"
            ):
                adapter.read_turn_metadata(run_id, turn_number, conn=mock_conn)

    def test_raises_valueerror_when_invalid_turn_metadata_data(
        self, adapter, mock_db_connection
    ):
        """Test that read_turn_metadata raises ValueError when TurnMetadata validation fails."""
        # Arrange: use valid turn_number=0 for the call (passes validate_turn_number)
        # but mock row returns invalid turn_number=-1 to trigger TurnMetadata validation
        run_id = "run_123"
        turn_number = 0

        row_data = {
            "run_id": run_id,
            "turn_number": -1,  # Invalid: negative (triggers TurnMetadata validation)
            "total_actions": '{"like": 5}',
            "created_at": "2024_01_01-12:00:00",
        }
        mock_row = create_mock_row(row_data)

        with mock_db_connection() as (mock_conn, mock_cursor):
            mock_cursor.fetchone.return_value = mock_row

            # Act & Assert
            with pytest.raises(ValueError, match="Invalid turn metadata data"):
                adapter.read_turn_metadata(run_id, turn_number, conn=mock_conn)

    def test_raises_valueerror_when_invalid_action_type(
        self, adapter, default_test_data, mock_db_connection
    ):
        """Test that read_turn_metadata raises ValueError when action type is invalid."""
        # Arrange
        run_id = default_test_data["run_id"]
        turn_number = default_test_data["turn_number"]

        # Create a mock row with invalid action type
        row_data = {
            "run_id": run_id,
            "turn_number": turn_number,
            "total_actions": '{"invalid_action": 5}',
            "created_at": "2024_01_01-12:00:00",
        }
        mock_row = create_mock_row(row_data)

        with mock_db_connection() as (mock_conn, mock_cursor):
            mock_cursor.fetchone.return_value = mock_row

            # Act & Assert
            with pytest.raises(
                ValueError, match="Invalid action type in total_actions"
            ):
                adapter.read_turn_metadata(run_id, turn_number, conn=mock_conn)

    def test_calls_database_with_correct_parameters(self, adapter, mock_db_connection):
        """Test that read_turn_metadata calls database with correct parameters."""
        # Arrange
        run_id = "run_123"
        turn_number = 5

        with mock_db_connection() as (mock_conn, mock_cursor):
            mock_cursor.fetchone.return_value = None

            # Act
            adapter.read_turn_metadata(run_id, turn_number, conn=mock_conn)

            # Assert
            mock_conn.execute.assert_called_once()
            call_args = mock_conn.execute.call_args
            assert (
                "SELECT * FROM turn_metadata WHERE run_id = ? AND turn_number = ?"
                in str(call_args[0][0])
            )
            assert call_args[0][1] == (run_id, turn_number)


class TestSQLiteRunAdapterReadTurnMetadataForRun:
    """Tests for SQLiteRunAdapter.read_turn_metadata_for_run method."""

    def test_returns_turn_metadata_rows_in_turn_order(
        self, adapter, mock_db_connection
    ):
        run_id = "run_123"
        row_turn_0 = create_mock_row(
            {
                "run_id": run_id,
                "turn_number": 0,
                "total_actions": json.dumps({"like": 1, "comment": 0, "follow": 0}),
                "created_at": "2024_01_01-12:00:00",
            }
        )
        row_turn_1 = create_mock_row(
            {
                "run_id": run_id,
                "turn_number": 1,
                "total_actions": json.dumps({"like": 3, "comment": 1, "follow": 0}),
                "created_at": "2024_01_01-12:01:00",
            }
        )
        expected_turn_numbers = [0, 1]

        with mock_db_connection() as (mock_conn, mock_cursor):
            mock_cursor.fetchall.return_value = [row_turn_0, row_turn_1]

            result = adapter.read_turn_metadata_for_run(run_id, conn=mock_conn)

            assert [item.turn_number for item in result] == expected_turn_numbers
            assert result[1].total_actions[TurnAction.LIKE] == 3

    def test_returns_empty_list_when_no_rows(self, adapter, mock_db_connection):
        run_id = "run_123"
        expected_result: list[TurnMetadata] = []

        with mock_db_connection() as (mock_conn, mock_cursor):
            mock_cursor.fetchall.return_value = []

            result = adapter.read_turn_metadata_for_run(run_id, conn=mock_conn)

            assert result == expected_result

    def test_matches_single_turn_read_behavior(self, adapter, mock_db_connection):
        run_id = "run_123"
        turn_number = 0
        row_data = {
            "run_id": run_id,
            "turn_number": turn_number,
            "total_actions": json.dumps({"like": 7, "comment": 2, "follow": 1}),
            "created_at": "2024_01_01-12:00:00",
        }
        mock_row = create_mock_row(row_data)

        with mock_db_connection() as (mock_conn, mock_cursor):
            mock_cursor.fetchall.return_value = [mock_row]
            list_result = adapter.read_turn_metadata_for_run(run_id, conn=mock_conn)

        with mock_db_connection() as (mock_conn, mock_cursor):
            mock_cursor.fetchone.return_value = mock_row
            single_result = adapter.read_turn_metadata(
                run_id, turn_number, conn=mock_conn
            )

        assert len(list_result) == 1
        assert single_result is not None
        assert list_result[0] == single_result

    def test_raises_valueerror_for_invalid_run_id(self, adapter):
        mock_conn = Mock()
        with pytest.raises(ValueError, match="run_id cannot be empty"):
            adapter.read_turn_metadata_for_run("", conn=mock_conn)

    def test_raises_operational_error_on_database_error(
        self, adapter, mock_db_connection
    ):
        run_id = "run_123"
        db_error = sqlite3.OperationalError("Database locked")

        with mock_db_connection() as (mock_conn, mock_cursor):
            mock_conn.execute.side_effect = db_error

            with pytest.raises(sqlite3.OperationalError):
                adapter.read_turn_metadata_for_run(run_id, conn=mock_conn)

    def test_calls_database_with_correct_parameters(self, adapter, mock_db_connection):
        run_id = "run_123"

        with mock_db_connection() as (mock_conn, mock_cursor):
            mock_cursor.fetchall.return_value = []

            adapter.read_turn_metadata_for_run(run_id, conn=mock_conn)

            mock_conn.execute.assert_called_once()
            call_args = mock_conn.execute.call_args
            assert (
                "SELECT * FROM turn_metadata WHERE run_id = ? ORDER BY turn_number ASC"
                in str(call_args[0][0])
            )
            assert call_args[0][1] == (run_id,)


class TestSQLiteRunAdapterWriteTurnMetadata:
    """Tests for SQLiteRunAdapter.write_turn_metadata method."""

    def test_writes_turn_metadata_successfully(
        self, adapter, default_test_data, mock_db_connection
    ):
        """Test that write_turn_metadata writes metadata to table successfully."""
        # Arrange
        run_id = default_test_data["run_id"]
        turn_number = default_test_data["turn_number"]

        turn_metadata = TurnMetadataFactory.create(
            run_id=run_id,
            turn_number=turn_number,
            total_actions={
                TurnAction.LIKE: 5,
                TurnAction.COMMENT: 2,
                TurnAction.FOLLOW: 1,
            },
            created_at="2024_01_01-12:00:00",
        )

        # Mock read_turn_metadata to return None (no duplicate)
        adapter.read_turn_metadata = Mock(return_value=None)

        with mock_db_connection() as (mock_conn, mock_cursor):
            # Act
            adapter.write_turn_metadata(turn_metadata, conn=mock_conn)

            # Assert
            # Verify read_turn_metadata was called to check for duplicates
            adapter.read_turn_metadata.assert_called_once_with(
                run_id, turn_number, conn=mock_conn
            )
            # Verify INSERT was executed (conn provided, no commit)
            mock_conn.execute.assert_called_once()
            call_args = mock_conn.execute.call_args
            assert "INSERT INTO turn_metadata" in str(call_args[0][0])
            # Verify parameters
            params = call_args[0][1]
            assert params[0] == run_id
            assert params[1] == turn_number
            # Parse JSON and compare dict to avoid key ordering issues
            assert json.loads(params[2]) == {"like": 5, "comment": 2, "follow": 1}
            assert params[3] == "2024_01_01-12:00:00"

    def test_write_turn_metadata_with_conn_does_not_commit(
        self, adapter, default_test_data
    ):
        """When conn is passed, write_turn_metadata uses it and does not call commit."""
        run_id = default_test_data["run_id"]
        turn_number = default_test_data["turn_number"]
        turn_metadata = TurnMetadataFactory.create(
            run_id=run_id,
            turn_number=turn_number,
            total_actions={TurnAction.LIKE: 1},
            created_at="2024_01_01-12:00:00",
        )
        mock_conn = Mock()
        mock_conn.execute = Mock()
        adapter.read_turn_metadata = Mock(return_value=None)

        adapter.write_turn_metadata(turn_metadata, conn=mock_conn)

        mock_conn.execute.assert_called_once()
        mock_conn.commit.assert_not_called()

    def test_raises_duplicate_turn_metadata_error_when_already_exists(
        self, adapter, default_test_data
    ):
        """Test that write_turn_metadata raises DuplicateTurnMetadataError when metadata already exists."""
        # Arrange
        from simulation.core.utils.exceptions import DuplicateTurnMetadataError

        run_id = default_test_data["run_id"]
        turn_number = default_test_data["turn_number"]

        turn_metadata = TurnMetadataFactory.create(
            run_id=run_id,
            turn_number=turn_number,
            total_actions={TurnAction.LIKE: 5},
            created_at="2024_01_01-12:00:00",
        )

        # Mock read_turn_metadata to return existing metadata (duplicate)
        existing_metadata = TurnMetadataFactory.create(
            run_id=run_id,
            turn_number=turn_number,
            total_actions={TurnAction.LIKE: 3},
            created_at="2024_01_01-11:00:00",
        )
        adapter.read_turn_metadata = Mock(return_value=existing_metadata)
        mock_conn = Mock()

        # Act & Assert
        with pytest.raises(
            DuplicateTurnMetadataError,
            match=f"Turn metadata already exists for run '{run_id}', turn {turn_number}",
        ):
            adapter.write_turn_metadata(turn_metadata, conn=mock_conn)

        # Verify read_turn_metadata was called
        adapter.read_turn_metadata.assert_called_once_with(
            run_id, turn_number, conn=mock_conn
        )

    def test_raises_operational_error_on_database_error(
        self, adapter, default_test_data, mock_db_connection
    ):
        """Test that write_turn_metadata raises OperationalError on database errors."""
        # Arrange
        run_id = default_test_data["run_id"]
        turn_number = default_test_data["turn_number"]

        turn_metadata = TurnMetadataFactory.create(
            run_id=run_id,
            turn_number=turn_number,
            total_actions={TurnAction.LIKE: 5},
            created_at="2024_01_01-12:00:00",
        )

        # Mock read_turn_metadata to return None (no duplicate)
        adapter.read_turn_metadata = Mock(return_value=None)

        db_error = sqlite3.OperationalError("Database locked")
        with mock_db_connection() as (mock_conn, mock_cursor):
            mock_conn.execute.side_effect = db_error

            # Act & Assert
            with pytest.raises(sqlite3.OperationalError):
                adapter.write_turn_metadata(turn_metadata, conn=mock_conn)

    def test_serializes_total_actions_to_json_correctly(
        self, adapter, default_test_data, mock_db_connection
    ):
        """Test that write_turn_metadata correctly serializes total_actions to JSON."""
        # Arrange
        run_id = default_test_data["run_id"]
        turn_number = default_test_data["turn_number"]

        turn_metadata = TurnMetadataFactory.create(
            run_id=run_id,
            turn_number=turn_number,
            total_actions={
                TurnAction.LIKE: 10,
                TurnAction.COMMENT: 5,
                TurnAction.FOLLOW: 3,
            },
            created_at="2024_01_01-12:00:00",
        )

        # Mock read_turn_metadata to return None (no duplicate)
        adapter.read_turn_metadata = Mock(return_value=None)

        with mock_db_connection() as (mock_conn, mock_cursor):
            # Act
            adapter.write_turn_metadata(turn_metadata, conn=mock_conn)

            # Assert
            call_args = mock_conn.execute.call_args
            params = call_args[0][1]
            total_actions_json = params[2]
            # Verify JSON serialization uses enum values as strings (parse and compare dict for order-independence)
            parsed = json.loads(total_actions_json)
            assert parsed == {"like": 10, "comment": 5, "follow": 3}

    def test_calls_database_with_correct_insert_parameters(
        self, adapter, mock_db_connection
    ):
        """Test that write_turn_metadata calls database with correct INSERT parameters."""
        # Arrange
        run_id = "run_456"
        turn_number = 3

        turn_metadata = TurnMetadataFactory.create(
            run_id=run_id,
            turn_number=turn_number,
            total_actions={TurnAction.LIKE: 7},
            created_at="2024_02_02-15:30:45",
        )

        # Mock read_turn_metadata to return None (no duplicate)
        adapter.read_turn_metadata = Mock(return_value=None)

        with mock_db_connection() as (mock_conn, mock_cursor):
            # Act
            adapter.write_turn_metadata(turn_metadata, conn=mock_conn)

            # Assert
            mock_conn.execute.assert_called_once()
            call_args = mock_conn.execute.call_args
            # Verify SQL statement
            sql = str(call_args[0][0])
            assert "INSERT INTO turn_metadata" in sql
            assert "run_id" in sql
            assert "turn_number" in sql
            assert "total_actions" in sql
            assert "created_at" in sql
            # Verify parameters tuple
            params = call_args[0][1]
            assert len(params) == 4
            assert params == (
                run_id,
                turn_number,
                json.dumps({"like": 7}),
                "2024_02_02-15:30:45",
            )

    def test_converts_integrity_error_to_duplicate_turn_metadata_error(
        self, adapter, default_test_data, mock_db_connection
    ):
        """Test that write_turn_metadata converts IntegrityError to DuplicateTurnMetadataError.

        This handles race conditions and edge cases where the pre-check passes
        but the INSERT fails due to a PRIMARY KEY constraint violation.
        """
        # Arrange
        from simulation.core.utils.exceptions import DuplicateTurnMetadataError

        run_id = default_test_data["run_id"]
        turn_number = default_test_data["turn_number"]

        turn_metadata = TurnMetadataFactory.create(
            run_id=run_id,
            turn_number=turn_number,
            total_actions={TurnAction.LIKE: 5},
            created_at="2024_01_01-12:00:00",
        )

        # Mock read_turn_metadata to return None (pre-check passes)
        adapter.read_turn_metadata = Mock(return_value=None)

        # Simulate PRIMARY KEY constraint violation (duplicate insert)
        integrity_error = sqlite3.IntegrityError(
            "UNIQUE constraint failed: turn_metadata.run_id, turn_metadata.turn_number"
        )
        with mock_db_connection() as (mock_conn, mock_cursor):
            mock_conn.execute.side_effect = integrity_error

            # Act & Assert
            with pytest.raises(
                DuplicateTurnMetadataError,
                match=f"Turn metadata already exists for run '{run_id}', turn {turn_number}",
            ):
                adapter.write_turn_metadata(turn_metadata, conn=mock_conn)

            # Verify read_turn_metadata was called (pre-check)
            adapter.read_turn_metadata.assert_called_once_with(
                run_id, turn_number, conn=mock_conn
            )
            # Verify INSERT was attempted (commit not used when conn provided)
            mock_conn.execute.assert_called_once()

    def test_does_not_commit_on_integrity_error(
        self, adapter, default_test_data, mock_db_connection
    ):
        """Test that commit is not called when IntegrityError is raised."""
        # Arrange
        from simulation.core.utils.exceptions import DuplicateTurnMetadataError

        run_id = default_test_data["run_id"]
        turn_number = default_test_data["turn_number"]

        turn_metadata = TurnMetadataFactory.create(
            run_id=run_id,
            turn_number=turn_number,
            total_actions={TurnAction.LIKE: 5},
            created_at="2024_01_01-12:00:00",
        )

        adapter.read_turn_metadata = Mock(return_value=None)
        integrity_error = sqlite3.IntegrityError("UNIQUE constraint failed")
        with mock_db_connection() as (mock_conn, mock_cursor):
            mock_conn.execute.side_effect = integrity_error

            # Act & Assert
            with pytest.raises(DuplicateTurnMetadataError):
                adapter.write_turn_metadata(turn_metadata, conn=mock_conn)

            # Verify commit was never called (conn provided, adapter does not commit)
            mock_conn.commit.assert_not_called()


class TestSQLiteRunAdapterUpdateRunStatus:
    """Tests for SQLiteRunAdapter.update_run_status method."""

    def test_update_run_status_with_conn_does_not_commit(self, adapter):
        """When conn is passed, update_run_status uses it and does not call commit."""
        run_id = "run_123"
        status = "completed"
        completed_at = "2026-01-01T00:00:00"
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.rowcount = 1
        mock_conn.execute.return_value = mock_cursor

        adapter.update_run_status(
            run_id=run_id,
            status=status,
            completed_at=completed_at,
            conn=mock_conn,
        )

        mock_conn.execute.assert_called_once()
        mock_conn.commit.assert_not_called()
