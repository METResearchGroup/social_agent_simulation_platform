"""Tests for simulation.api.services.run_query_service."""

from unittest.mock import MagicMock

import pytest

from simulation.api.errors import ApiRunNotFoundError
from simulation.api.services.run_query_service import get_run_details
from simulation.core.models.actions import TurnAction
from simulation.core.models.runs import RunStatus
from tests.factories import RunFactory, TurnMetadataFactory


def test_get_run_details_returns_sorted_turns_with_string_action_keys():
    """Run details include sorted turns and JSON-safe action key names."""
    mock_engine = MagicMock()
    run = RunFactory.create(
        run_id="run-query-1",
        created_at="2026-01-01T00:00:00",
        total_turns=2,
        total_agents=2,
        feed_algorithm="chronological",
        metric_keys=[
            "run.actions.total",
            "run.actions.total_by_type",
            "turn.actions.counts_by_type",
            "turn.actions.total",
        ],
        started_at="2026-01-01T00:00:00",
        status=RunStatus.COMPLETED,
        completed_at="2026-01-01T00:01:00",
    )
    metadata_list = [
        TurnMetadataFactory.create(
            run_id=run.run_id,
            turn_number=1,
            total_actions={TurnAction.LIKE: 3},
            created_at="2026-01-01T00:00:02",
        ),
        TurnMetadataFactory.create(
            run_id=run.run_id,
            turn_number=0,
            total_actions={TurnAction.FOLLOW: 1, TurnAction.COMMENT: 2},
            created_at="2026-01-01T00:00:01",
        ),
    ]
    mock_engine.get_run.return_value = run
    mock_engine.list_turn_metadata.return_value = metadata_list
    mock_engine.list_turn_metrics.return_value = []
    mock_engine.get_run_metrics.return_value = None

    result = get_run_details(run_id=run.run_id, engine=mock_engine)

    assert result.config.feed_algorithm == "chronological"
    assert [item.turn_number for item in result.turns] == [0, 1]
    assert result.turns[0].total_actions == {"follow": 1, "comment": 2}
    assert result.turns[1].total_actions == {"like": 3}


def test_get_run_details_raises_run_not_found_for_missing_run():
    """Missing run raises ApiRunNotFoundError for route-level 404 mapping."""
    mock_engine = MagicMock()
    mock_engine.get_run.return_value = None

    with pytest.raises(ApiRunNotFoundError):
        get_run_details(run_id="missing-run", engine=mock_engine)
