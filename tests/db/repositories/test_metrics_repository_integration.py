"""Integration tests for db.repositories.metrics_repository module."""

import os
import tempfile

import pytest

from db.adapters.sqlite.sqlite import DB_PATH, initialize_database
from db.repositories.metrics_repository import create_sqlite_metrics_repository
from db.repositories.run_repository import create_sqlite_repository
from lib.timestamp_utils import get_current_timestamp
from simulation.core.models.metrics import RunMetrics, TurnMetrics
from simulation.core.models.runs import RunConfig


@pytest.fixture
def temp_db():
    """Create a temporary database for integration tests."""
    original_path = DB_PATH

    fd, temp_path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)

    import db.adapters.sqlite.sqlite as sqlite_module

    sqlite_module.DB_PATH = temp_path
    initialize_database()

    yield temp_path

    sqlite_module.DB_PATH = original_path
    if os.path.exists(temp_path):
        os.unlink(temp_path)


class TestSQLiteMetricsRepositoryIntegration:
    """Integration tests using a real SQLite database."""

    def test_write_and_read_turn_metrics(self, temp_db):
        """write_turn_metrics then get_turn_metrics round-trips."""
        run_repo = create_sqlite_repository()
        metrics_repo = create_sqlite_metrics_repository()

        run = run_repo.create_run(
            RunConfig(num_agents=2, num_turns=2, feed_algorithm="chronological")
        )

        created_at = get_current_timestamp()
        turn_metrics = TurnMetrics(
            run_id=run.run_id,
            turn_number=0,
            metrics={"turn.actions.total": 3},
            created_at=created_at,
        )
        metrics_repo.write_turn_metrics(turn_metrics)

        result = metrics_repo.get_turn_metrics(run.run_id, 0)

        assert result is not None
        assert result.run_id == run.run_id
        assert result.turn_number == 0
        assert result.metrics == {"turn.actions.total": 3}
        assert result.created_at == created_at

    def test_list_turn_metrics_is_ordered_by_turn_number(self, temp_db):
        """list_turn_metrics returns items ordered by turn_number ascending."""
        run_repo = create_sqlite_repository()
        metrics_repo = create_sqlite_metrics_repository()

        run = run_repo.create_run(
            RunConfig(num_agents=2, num_turns=3, feed_algorithm="chronological")
        )

        metrics_repo.write_turn_metrics(
            TurnMetrics(
                run_id=run.run_id,
                turn_number=2,
                metrics={"k": 2},
                created_at=get_current_timestamp(),
            )
        )
        metrics_repo.write_turn_metrics(
            TurnMetrics(
                run_id=run.run_id,
                turn_number=0,
                metrics={"k": 0},
                created_at=get_current_timestamp(),
            )
        )
        metrics_repo.write_turn_metrics(
            TurnMetrics(
                run_id=run.run_id,
                turn_number=1,
                metrics={"k": 1},
                created_at=get_current_timestamp(),
            )
        )

        result = metrics_repo.list_turn_metrics(run.run_id)
        expected_turn_numbers = [0, 1, 2]

        assert [item.turn_number for item in result] == expected_turn_numbers

    def test_write_and_read_run_metrics(self, temp_db):
        """write_run_metrics then get_run_metrics round-trips."""
        run_repo = create_sqlite_repository()
        metrics_repo = create_sqlite_metrics_repository()

        run = run_repo.create_run(
            RunConfig(num_agents=1, num_turns=1, feed_algorithm="chronological")
        )

        created_at = get_current_timestamp()
        run_metrics = RunMetrics(
            run_id=run.run_id,
            metrics={"run.actions.total": 7},
            created_at=created_at,
        )
        metrics_repo.write_run_metrics(run_metrics)

        result = metrics_repo.get_run_metrics(run.run_id)

        assert result is not None
        assert result.run_id == run.run_id
        assert result.metrics == {"run.actions.total": 7}
        assert result.created_at == created_at
