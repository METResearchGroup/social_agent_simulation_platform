"""Integration tests for db.repositories.metrics_repository module."""

from __future__ import annotations

import json
import sqlite3

from db.adapters.sqlite.turn_parent import TURN_PARENT_PLACEHOLDER_CREATED_AT
from lib.timestamp_utils import get_current_timestamp
from simulation.core.models.actions import TurnAction
from tests.factories import RunConfigFactory, RunMetricsFactory, TurnMetricsFactory


def _seed_turn_parent_row(temp_db: str, run_id: str, turn_number: int) -> None:
    conn = sqlite3.connect(temp_db)
    try:
        conn.execute(
            """
            INSERT OR IGNORE INTO turns (run_id, turn_number, total_actions, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                run_id,
                turn_number,
                json.dumps({k.value: 0 for k in TurnAction}),
                TURN_PARENT_PLACEHOLDER_CREATED_AT,
            ),
        )
        conn.commit()
    finally:
        conn.close()


class TestSQLiteMetricsRepositoryIntegration:
    """Integration tests using a real SQLite database."""

    def test_write_and_read_turn_metrics(self, temp_db, run_repo, metrics_repo):
        """write_turn_metrics then get_turn_metrics round-trips."""
        run = run_repo.create_run(
            RunConfigFactory.create(
                num_agents=2, num_turns=2, feed_algorithm="chronological"
            )
        )
        _seed_turn_parent_row(temp_db, run.run_id, 0)

        created_at = get_current_timestamp()
        turn_metrics = TurnMetricsFactory.create(
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

    def test_list_turn_metrics_is_ordered_by_turn_number(
        self, temp_db, run_repo, metrics_repo
    ):
        """list_turn_metrics returns items ordered by turn_number ascending."""
        run = run_repo.create_run(
            RunConfigFactory.create(
                num_agents=2, num_turns=3, feed_algorithm="chronological"
            )
        )
        for tn in (0, 1, 2):
            _seed_turn_parent_row(temp_db, run.run_id, tn)

        metrics_repo.write_turn_metrics(
            TurnMetricsFactory.create(
                run_id=run.run_id,
                turn_number=2,
                metrics={"k": 2},
                created_at=get_current_timestamp(),
            )
        )
        metrics_repo.write_turn_metrics(
            TurnMetricsFactory.create(
                run_id=run.run_id,
                turn_number=0,
                metrics={"k": 0},
                created_at=get_current_timestamp(),
            )
        )
        metrics_repo.write_turn_metrics(
            TurnMetricsFactory.create(
                run_id=run.run_id,
                turn_number=1,
                metrics={"k": 1},
                created_at=get_current_timestamp(),
            )
        )

        result = metrics_repo.list_turn_metrics(run.run_id)
        expected_turn_numbers = [0, 1, 2]

        assert [item.turn_number for item in result] == expected_turn_numbers

    def test_write_and_read_run_metrics(self, run_repo, metrics_repo):
        """write_run_metrics then get_run_metrics round-trips."""
        run = run_repo.create_run(
            RunConfigFactory.create(
                num_agents=1, num_turns=1, feed_algorithm="chronological"
            )
        )

        created_at = get_current_timestamp()
        run_metrics = RunMetricsFactory.create(
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
