"""Tests for simulation.api.services.run_query_service."""

from unittest.mock import MagicMock

import pytest

from lib.agent_id import canonical_agent_id
from simulation.api.errors import ApiRunNotFoundError
from simulation.api.services.run_query_service import get_run_details, get_turns_for_run
from simulation.core.models.actions import Like, TurnAction
from simulation.core.models.generated.base import GenerationMetadata
from simulation.core.models.generated.like import GeneratedLike
from simulation.core.models.runs import RunStatus
from simulation.core.models.turns import TurnData
from tests.factories import (
    GeneratedFeedFactory,
    RunAgentSnapshotFactory,
    RunFactory,
    TurnMetadataFactory,
)


class TestRunQueryService:
    def test_get_run_details_returns_sorted_turns_with_string_action_keys(self):
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

    def test_get_run_details_raises_run_not_found_for_missing_run(self):
        """Missing run raises ApiRunNotFoundError for route-level 404 mapping."""
        mock_engine = MagicMock()
        mock_engine.get_run.return_value = None

        with pytest.raises(ApiRunNotFoundError):
            get_run_details(run_id="missing-run", engine=mock_engine)

    def test_get_turns_for_run_returns_empty_maps_when_get_turn_data_is_none(self):
        """Persisted turn metadata still yields a TurnSchema when there is no turn data."""
        mock_engine = MagicMock()
        run = RunFactory.create(
            run_id="run-turns-empty-1",
            created_at="2026-01-01T00:00:00",
            total_turns=1,
            total_agents=1,
            feed_algorithm="chronological",
            metric_keys=["turn.actions.total"],
            started_at="2026-01-01T00:00:00",
            status=RunStatus.COMPLETED,
            completed_at="2026-01-01T00:01:00",
        )
        mock_engine.get_run.return_value = run
        mock_engine.list_turn_metadata.return_value = [
            TurnMetadataFactory.create(
                run_id=run.run_id,
                turn_number=0,
                total_actions={},
                created_at="2026-01-01T00:00:00",
            )
        ]
        mock_engine.list_run_agents.return_value = []
        mock_engine.get_turn_data.return_value = None

        result = get_turns_for_run(run_id=run.run_id, engine=mock_engine)

        assert result["0"].turn_number == 0
        assert result["0"].agent_feeds == {}
        assert result["0"].agent_actions == {}
        mock_engine.get_turn_data.assert_called_once_with(run.run_id, 0)

    def test_get_turns_for_run_raises_when_run_missing(self):
        mock_engine = MagicMock()
        mock_engine.get_run.return_value = None
        with pytest.raises(ApiRunNotFoundError):
            get_turns_for_run(run_id="missing-run-id", engine=mock_engine)

    def test_get_turns_for_run_serializes_id_keyed_feeds_and_actions(self):
        """Turn payloads use canonical agent_id keys and include action rows."""
        mock_engine = MagicMock()
        run = RunFactory.create(
            run_id="run-turns-serialize-1",
            created_at="2026-01-01T00:00:00",
            total_turns=1,
            total_agents=1,
            feed_algorithm="chronological",
            metric_keys=["turn.actions.total"],
            started_at="2026-01-01T00:00:00",
            status=RunStatus.COMPLETED,
            completed_at="2026-01-01T00:01:00",
        )
        agent_id = canonical_agent_id("alice.bsky.social")
        feed = GeneratedFeedFactory.create(
            run_id=run.run_id,
            turn_number=0,
            agent_id=agent_id,
            agent_handle="alice.bsky.social",
            post_ids=["rp_1"],
        )
        meta = GenerationMetadata(
            model_used=None,
            generation_metadata=None,
            created_at="2026-01-01T00:00:00Z",
        )
        generated_like = GeneratedLike(
            like=Like(
                like_id="like_1",
                agent_id=agent_id,
                post_id="rp_1",
                created_at="2026-01-01T00:00:01Z",
            ),
            explanation="nice",
            metadata=meta,
        )
        turn_data = TurnData(
            turn_number=0,
            agents=[],
            feeds={agent_id: []},
            feed_records={agent_id: feed},
            actions={agent_id: [generated_like]},
        )
        mock_engine.get_run.return_value = run
        mock_engine.list_turn_metadata.return_value = [
            TurnMetadataFactory.create(
                run_id=run.run_id,
                turn_number=0,
                total_actions={TurnAction.LIKE: 1},
                created_at="2026-01-01T00:00:00",
            )
        ]
        mock_engine.list_run_agents.return_value = [
            RunAgentSnapshotFactory.create(
                run_id=run.run_id,
                agent_id=agent_id,
                handle_at_start="alice.bsky.social",
            )
        ]
        mock_engine.get_turn_data.return_value = turn_data

        result = get_turns_for_run(run_id=run.run_id, engine=mock_engine)

        assert set(result["0"].agent_feeds.keys()) == {agent_id}
        feed_schema = result["0"].agent_feeds[agent_id]
        assert feed_schema.agent_id == agent_id
        assert feed_schema.agent_handle == "alice.bsky.social"
        assert set(result["0"].agent_actions.keys()) == {agent_id}
        actions = result["0"].agent_actions[agent_id]
        assert len(actions) == 1
        assert actions[0].type == TurnAction.LIKE
        assert actions[0].agent_id == agent_id
        assert actions[0].agent_handle == "alice.bsky.social"
        assert actions[0].post_id == "rp_1"
        assert actions[0].target_agent_id is None
