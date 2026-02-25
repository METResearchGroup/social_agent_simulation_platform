from __future__ import annotations

from unittest.mock import MagicMock

from lib.timestamp_utils import get_current_timestamp
from simulation.core.models.actions import TurnAction
from simulation.core.models.runs import RunStatus
from tests.factories.metrics import RunMetricsFactory, TurnMetricsFactory
from tests.factories.runs import RunFactory
from tests.factories.turns import TurnMetadataFactory


class EngineFactory:
    @classmethod
    def create_completed_run_engine(
        cls,
        *,
        run_id: str,
        total_turns: int,
        total_agents: int,
        metric_keys: list[str] | None = None,
        created_at: str | None = None,
    ) -> MagicMock:
        created_at_value = (
            created_at if created_at is not None else get_current_timestamp()
        )
        keys = (
            metric_keys
            if metric_keys is not None
            else [
                "run.actions.total",
                "run.actions.total_by_type",
                "turn.actions.counts_by_type",
                "turn.actions.total",
            ]
        )
        run = RunFactory.create(
            run_id=run_id,
            created_at=created_at_value,
            total_turns=total_turns,
            total_agents=total_agents,
            feed_algorithm="chronological",
            metric_keys=keys,
            started_at=created_at_value,
            status=RunStatus.COMPLETED,
            completed_at=created_at_value,
        )

        metadata_list = [
            TurnMetadataFactory.create(
                run_id=run_id,
                turn_number=i,
                total_actions={
                    TurnAction.LIKE: 0,
                    TurnAction.COMMENT: 0,
                    TurnAction.FOLLOW: 0,
                },
                created_at=created_at_value,
            )
            for i in range(total_turns)
        ]
        turn_metrics_list = [
            TurnMetricsFactory.create(
                run_id=run_id,
                turn_number=i,
                metrics={"turn.actions.total": 0},
                created_at=created_at_value,
            )
            for i in range(total_turns)
        ]
        run_metrics = RunMetricsFactory.create(
            run_id=run_id,
            metrics={"run.actions.total": 0},
            created_at=created_at_value,
        )

        mock = MagicMock()
        mock.execute_run.return_value = run
        mock.list_turn_metadata.return_value = metadata_list
        mock.list_turn_metrics.return_value = turn_metrics_list
        mock.get_run_metrics.return_value = run_metrics
        mock.get_run.return_value = run
        return mock
