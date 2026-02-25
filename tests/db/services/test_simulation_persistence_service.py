"""Tests for SimulationPersistenceService."""

from contextlib import contextmanager
from unittest.mock import Mock

import pytest

from db.services.simulation_persistence_service import (
    SimulationPersistenceService,
    create_simulation_persistence_service,
)
from simulation.core.models.actions import TurnAction
from simulation.core.models.runs import RunStatus
from tests.factories import RunMetricsFactory, TurnMetadataFactory, TurnMetricsFactory


@pytest.fixture
def mock_run_repo():
    return Mock()


@pytest.fixture
def mock_metrics_repo():
    return Mock()


@pytest.fixture
def mock_transaction_provider():
    """TransactionProvider that yields a single mock conn so both repos receive the same conn."""

    class MockTransactionProvider:
        @contextmanager
        def run_transaction(self):
            conn = Mock()
            yield conn

    return MockTransactionProvider()


@pytest.fixture
def mock_like_repo():
    return Mock()


@pytest.fixture
def mock_comment_repo():
    return Mock()


@pytest.fixture
def mock_follow_repo():
    return Mock()


@pytest.fixture
def sample_turn_metadata():
    return TurnMetadataFactory.create(
        run_id="run_1",
        turn_number=0,
        total_actions={
            TurnAction.LIKE: 1,
            TurnAction.COMMENT: 0,
            TurnAction.FOLLOW: 0,
        },
        created_at="2026-01-01T00:00:00",
    )


@pytest.fixture
def sample_turn_metrics():
    return TurnMetricsFactory.create(
        run_id="run_1",
        turn_number=0,
        metrics={"turn.actions.total": 1},
        created_at="2026-01-01T00:00:00",
    )


@pytest.fixture
def sample_run_metrics():
    return RunMetricsFactory.create(
        run_id="run_1",
        metrics={"run.actions.total": 10},
        created_at="2026-01-01T00:00:00",
    )


class TestCreateSimulationPersistenceService:
    def test_returns_simulation_persistence_service(
        self,
        mock_run_repo,
        mock_metrics_repo,
        mock_transaction_provider,
        mock_like_repo,
        mock_comment_repo,
        mock_follow_repo,
    ):
        service = create_simulation_persistence_service(
            run_repo=mock_run_repo,
            metrics_repo=mock_metrics_repo,
            transaction_provider=mock_transaction_provider,
            like_repo=mock_like_repo,
            comment_repo=mock_comment_repo,
            follow_repo=mock_follow_repo,
        )
        assert isinstance(service, SimulationPersistenceService)


class TestSimulationPersistenceServiceWriteTurn:
    def test_calls_both_repos_with_same_conn(
        self,
        mock_run_repo,
        mock_metrics_repo,
        mock_transaction_provider,
        mock_like_repo,
        mock_comment_repo,
        mock_follow_repo,
        sample_turn_metadata,
        sample_turn_metrics,
    ):
        """When write_turn is called, both write_turn_metadata and write_turn_metrics receive the same conn."""
        service = SimulationPersistenceService(
            run_repo=mock_run_repo,
            metrics_repo=mock_metrics_repo,
            transaction_provider=mock_transaction_provider,
            like_repo=mock_like_repo,
            comment_repo=mock_comment_repo,
            follow_repo=mock_follow_repo,
        )
        service.write_turn(
            turn_metadata=sample_turn_metadata,
            turn_metrics=sample_turn_metrics,
        )
        assert mock_run_repo.write_turn_metadata.called
        assert mock_metrics_repo.write_turn_metrics.called
        call_metadata = mock_run_repo.write_turn_metadata.call_args
        call_metrics = mock_metrics_repo.write_turn_metrics.call_args
        assert call_metadata.kwargs.get("conn") is not None
        assert call_metrics.kwargs.get("conn") is not None
        assert call_metadata.kwargs["conn"] is call_metrics.kwargs["conn"]

    def test_passes_metadata_and_metrics_to_repos(
        self,
        mock_run_repo,
        mock_metrics_repo,
        mock_transaction_provider,
        mock_like_repo,
        mock_comment_repo,
        mock_follow_repo,
        sample_turn_metadata,
        sample_turn_metrics,
    ):
        service = SimulationPersistenceService(
            run_repo=mock_run_repo,
            metrics_repo=mock_metrics_repo,
            transaction_provider=mock_transaction_provider,
            like_repo=mock_like_repo,
            comment_repo=mock_comment_repo,
            follow_repo=mock_follow_repo,
        )
        service.write_turn(
            turn_metadata=sample_turn_metadata,
            turn_metrics=sample_turn_metrics,
        )
        mock_run_repo.write_turn_metadata.assert_called_once()
        assert mock_run_repo.write_turn_metadata.call_args[0][0] == sample_turn_metadata
        mock_metrics_repo.write_turn_metrics.assert_called_once()
        assert (
            mock_metrics_repo.write_turn_metrics.call_args[0][0] == sample_turn_metrics
        )

    def test_exception_from_write_turn_metadata_propagates(
        self,
        mock_run_repo,
        mock_metrics_repo,
        mock_transaction_provider,
        mock_like_repo,
        mock_comment_repo,
        mock_follow_repo,
        sample_turn_metadata,
        sample_turn_metrics,
    ):
        from simulation.core.exceptions import DuplicateTurnMetadataError

        mock_run_repo.write_turn_metadata.side_effect = DuplicateTurnMetadataError(
            "run_1", 0
        )
        service = SimulationPersistenceService(
            run_repo=mock_run_repo,
            metrics_repo=mock_metrics_repo,
            transaction_provider=mock_transaction_provider,
            like_repo=mock_like_repo,
            comment_repo=mock_comment_repo,
            follow_repo=mock_follow_repo,
        )
        with pytest.raises(DuplicateTurnMetadataError):
            service.write_turn(
                turn_metadata=sample_turn_metadata,
                turn_metrics=sample_turn_metrics,
            )
        mock_metrics_repo.write_turn_metrics.assert_not_called()

    def test_exception_from_write_turn_metrics_propagates(
        self,
        mock_run_repo,
        mock_metrics_repo,
        mock_transaction_provider,
        mock_like_repo,
        mock_comment_repo,
        mock_follow_repo,
        sample_turn_metadata,
        sample_turn_metrics,
    ):
        mock_metrics_repo.write_turn_metrics.side_effect = RuntimeError("db error")
        service = SimulationPersistenceService(
            run_repo=mock_run_repo,
            metrics_repo=mock_metrics_repo,
            transaction_provider=mock_transaction_provider,
            like_repo=mock_like_repo,
            comment_repo=mock_comment_repo,
            follow_repo=mock_follow_repo,
        )
        with pytest.raises(RuntimeError):
            service.write_turn(
                turn_metadata=sample_turn_metadata,
                turn_metrics=sample_turn_metrics,
            )
        mock_run_repo.write_turn_metadata.assert_called_once()


class TestSimulationPersistenceServiceWriteRun:
    def test_calls_write_run_metrics_and_update_run_status(
        self,
        mock_run_repo,
        mock_metrics_repo,
        mock_transaction_provider,
        mock_like_repo,
        mock_comment_repo,
        mock_follow_repo,
        sample_run_metrics,
    ):
        """When write_run is called, write_run_metrics and update_run_status are invoked in one transaction."""
        service = SimulationPersistenceService(
            run_repo=mock_run_repo,
            metrics_repo=mock_metrics_repo,
            transaction_provider=mock_transaction_provider,
            like_repo=mock_like_repo,
            comment_repo=mock_comment_repo,
            follow_repo=mock_follow_repo,
        )
        service.write_run(run_id="run_1", run_metrics=sample_run_metrics)
        mock_metrics_repo.write_run_metrics.assert_called_once()
        assert mock_metrics_repo.write_run_metrics.call_args[0][0] == sample_run_metrics
        mock_run_repo.update_run_status.assert_called_once_with(
            "run_1",
            RunStatus.COMPLETED,
            conn=mock_metrics_repo.write_run_metrics.call_args[1]["conn"],
        )
        # Both called with same conn (transaction)
        write_conn = mock_metrics_repo.write_run_metrics.call_args[1]["conn"]
        status_conn = mock_run_repo.update_run_status.call_args[1]["conn"]
        assert write_conn is status_conn

    def test_passes_run_id_and_run_metrics(
        self,
        mock_run_repo,
        mock_metrics_repo,
        mock_transaction_provider,
        mock_like_repo,
        mock_comment_repo,
        mock_follow_repo,
        sample_run_metrics,
    ):
        service = SimulationPersistenceService(
            run_repo=mock_run_repo,
            metrics_repo=mock_metrics_repo,
            transaction_provider=mock_transaction_provider,
            like_repo=mock_like_repo,
            comment_repo=mock_comment_repo,
            follow_repo=mock_follow_repo,
        )
        service.write_run(run_id="run_1", run_metrics=sample_run_metrics)
        mock_metrics_repo.write_run_metrics.assert_called_once()
        assert mock_metrics_repo.write_run_metrics.call_args[0][0] == sample_run_metrics
        assert mock_run_repo.update_run_status.call_count == 1
        assert mock_run_repo.update_run_status.call_args[0][:2] == (
            "run_1",
            RunStatus.COMPLETED,
        )
        assert "conn" in mock_run_repo.update_run_status.call_args[1]

    def test_exception_from_write_run_metrics_propagates(
        self,
        mock_run_repo,
        mock_metrics_repo,
        mock_transaction_provider,
        mock_like_repo,
        mock_comment_repo,
        mock_follow_repo,
        sample_run_metrics,
    ):
        mock_metrics_repo.write_run_metrics.side_effect = RuntimeError("db error")
        service = SimulationPersistenceService(
            run_repo=mock_run_repo,
            metrics_repo=mock_metrics_repo,
            transaction_provider=mock_transaction_provider,
            like_repo=mock_like_repo,
            comment_repo=mock_comment_repo,
            follow_repo=mock_follow_repo,
        )
        with pytest.raises(RuntimeError):
            service.write_run(run_id="run_1", run_metrics=sample_run_metrics)
        mock_run_repo.update_run_status.assert_not_called()
