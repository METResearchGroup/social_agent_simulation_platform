"""Tests for TurnPersistenceService."""

from unittest.mock import Mock

import pytest

from db.services.turn_persistence_service import (
    TurnPersistenceService,
    create_turn_persistence_service,
)
from simulation.core.models.actions import TurnAction
from simulation.core.models.metrics import TurnMetrics
from simulation.core.models.turns import TurnMetadata


@pytest.fixture
def mock_run_repo():
    return Mock()


@pytest.fixture
def mock_metrics_repo():
    return Mock()


@pytest.fixture
def sample_turn_metadata():
    return TurnMetadata(
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
    return TurnMetrics(
        run_id="run_1",
        turn_number=0,
        metrics={"turn.actions.total": 1},
        created_at="2026-01-01T00:00:00",
    )


class TestCreateTurnPersistenceService:
    def test_returns_turn_persistence_service(self, mock_run_repo, mock_metrics_repo):
        service = create_turn_persistence_service(
            run_repo=mock_run_repo,
            metrics_repo=mock_metrics_repo,
        )
        assert isinstance(service, TurnPersistenceService)


class TestTurnPersistenceServiceWriteTurn:
    def test_calls_both_repos_with_same_conn(
        self,
        mock_run_repo,
        mock_metrics_repo,
        sample_turn_metadata,
        sample_turn_metrics,
    ):
        """When write_turn is called, both write_turn_metadata and write_turn_metrics receive the same conn."""
        service = TurnPersistenceService(
            run_repo=mock_run_repo,
            metrics_repo=mock_metrics_repo,
        )
        service.write_turn(
            turn_metadata=sample_turn_metadata,
            turn_metrics=sample_turn_metrics,
        )
        # run_transaction yields a conn; both repos must be called with that conn
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
        sample_turn_metadata,
        sample_turn_metrics,
    ):
        service = TurnPersistenceService(
            run_repo=mock_run_repo,
            metrics_repo=mock_metrics_repo,
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
        sample_turn_metadata,
        sample_turn_metrics,
    ):
        from simulation.core.exceptions import DuplicateTurnMetadataError

        mock_run_repo.write_turn_metadata.side_effect = DuplicateTurnMetadataError(
            "run_1", 0
        )
        service = TurnPersistenceService(
            run_repo=mock_run_repo,
            metrics_repo=mock_metrics_repo,
        )
        with pytest.raises(DuplicateTurnMetadataError):
            service.write_turn(
                turn_metadata=sample_turn_metadata,
                turn_metrics=sample_turn_metrics,
            )
        # write_turn_metrics is never called when write_turn_metadata raises first
        mock_metrics_repo.write_turn_metrics.assert_not_called()

    def test_exception_from_write_turn_metrics_propagates(
        self,
        mock_run_repo,
        mock_metrics_repo,
        sample_turn_metadata,
        sample_turn_metrics,
    ):
        mock_metrics_repo.write_turn_metrics.side_effect = RuntimeError("db error")
        service = TurnPersistenceService(
            run_repo=mock_run_repo,
            metrics_repo=mock_metrics_repo,
        )
        with pytest.raises(RuntimeError):
            service.write_turn(
                turn_metadata=sample_turn_metadata,
                turn_metrics=sample_turn_metrics,
            )
        mock_run_repo.write_turn_metadata.assert_called_once()
