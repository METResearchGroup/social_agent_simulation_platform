"""Tests for run_execution_service execute and validation."""

from unittest.mock import MagicMock

import pytest

from simulation.api.schemas.simulation import RunRequest
from simulation.api.services.run_execution_service import execute
from simulation.core.models.actions import TurnAction
from simulation.core.utils.exceptions import (
    InconsistentTurnDataError,
    SimulationRunFailure,
)
from tests.factories import TurnMetadataFactory, TurnMetricsFactory


def test_execute_raises_inconsistent_turn_data_on_mismatched_turn_sets():
    """When metadata and metrics have different turn number sets, execute raises InconsistentTurnDataError."""
    request = RunRequest(num_agents=2, num_turns=2)
    mock_engine = MagicMock()
    mock_engine.execute_run.side_effect = SimulationRunFailure(
        message="Run failed",
        run_id="run-mismatch-1",
        cause=RuntimeError("turn failed"),
    )
    # Metadata for turns 0 and 1, metrics only for turn 0 -> mismatch
    metadata_list = [
        TurnMetadataFactory.create(
            run_id="run-mismatch-1",
            turn_number=0,
            total_actions={
                TurnAction.LIKE: 0,
                TurnAction.COMMENT: 0,
                TurnAction.FOLLOW: 0,
            },
            created_at="2026-01-01T00:00:00",
        ),
        TurnMetadataFactory.create(
            run_id="run-mismatch-1",
            turn_number=1,
            total_actions={
                TurnAction.LIKE: 1,
                TurnAction.COMMENT: 0,
                TurnAction.FOLLOW: 0,
            },
            created_at="2026-01-01T00:00:01",
        ),
    ]
    turn_metrics_list = [
        TurnMetricsFactory.create(
            run_id="run-mismatch-1",
            turn_number=0,
            metrics={"turn.actions.total": 0},
            created_at="2026-01-01T00:00:00",
        )
    ]
    mock_engine.list_turn_metadata.return_value = metadata_list
    mock_engine.list_turn_metrics.return_value = turn_metrics_list

    with pytest.raises(InconsistentTurnDataError) as exc_info:
        execute(request=request, engine=mock_engine)

    assert exc_info.value.metadata_only == {1}
    assert exc_info.value.metrics_only == set()
