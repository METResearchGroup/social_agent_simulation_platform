"""Unit tests for run summary formatting."""

from __future__ import annotations

import sqlite3

from simulation_v2.db.models import RunRecord, TurnRecord
from simulation_v2.run_summary import (
    format_entity_delta,
    format_eval_summary,
    format_run_summary,
)


def _run(**overrides: object) -> RunRecord:
    defaults = {
        "run_id": "run-1",
        "status": "completed",
        "config_json": {},
        "seed_metadata_json": {
            "post_count": 50,
            "like_count": 100,
            "follow_count": 20,
        },
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    defaults.update(overrides)
    return RunRecord.model_validate(defaults)


def _turn(**overrides: object) -> TurnRecord:
    defaults = {
        "turn_id": "turn-1",
        "run_id": "run-1",
        "turn_number": 1,
        "status": "completed",
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    defaults.update(overrides)
    return TurnRecord.model_validate(defaults)


class TestFormatEntityDelta:
    def test_no_change(self) -> None:
        assert format_entity_delta(10, 10) == "10"

    def test_positive_delta(self) -> None:
        assert format_entity_delta(50, 52) == "52 (+2)"

    def test_negative_delta(self) -> None:
        assert format_entity_delta(10, 8) == "8 (-2)"


class TestFormatRunSummary:
    def test_includes_entity_deltas_and_pipeline_counts(self) -> None:
        lines = format_run_summary(
            run=_run(),
            turns=[_turn(), _turn(turn_id="turn-2", turn_number=2)],
            seed_meta={"post_count": 50, "like_count": 100, "follow_count": 20},
            totals={
                "user_count": 10,
                "post_count": 52,
                "like_count": 105,
                "follow_count": 22,
                "comment_count": 3,
                "memory_count": 10,
                "generation_count": 40,
                "proposed_action_count": 35,
                "generated_feed_count": 30,
                "eval_run_count": 8,
                "eval_metric_count": 12,
                "turn_count": 2,
            },
            eval_summary="Evals: 8 plugin runs (4 turn + 4 run scope), 12 metrics",
        )

        assert lines[0] == (
            "Run complete: run_id=run-1 status=completed completed_turns=2/2"
        )
        assert "posts=52 (+2)" in lines[1]
        assert "likes=105 (+5)" in lines[1]
        assert "follows=22 (+2)" in lines[1]
        assert "comments=3 (+3)" in lines[1]
        assert "generations=40" in lines[2]
        assert "generated_feeds=30" in lines[2]
        assert lines[3].startswith("Evals: 8 plugin runs")


def _eval_db(rows: list[tuple[str, str, str]]) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE eval_runs (
            eval_run_id TEXT PRIMARY KEY,
            run_id TEXT,
            turn_id TEXT,
            scope TEXT,
            plugin_name TEXT,
            status TEXT,
            created_at TEXT,
            finished_at TEXT,
            error TEXT
        );
        CREATE TABLE eval_metrics (
            eval_metric_id TEXT PRIMARY KEY,
            eval_run_id TEXT,
            run_id TEXT,
            turn_id TEXT,
            plugin_name TEXT,
            metric_name TEXT,
            metric_value REAL,
            metadata_json TEXT,
            created_at TEXT
        );
        """
    )
    for scope, plugin_name, status in rows:
        conn.execute(
            """
            INSERT INTO eval_runs (
                eval_run_id, run_id, turn_id, scope, plugin_name,
                status, created_at, finished_at, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"eval-{plugin_name}",
                "run-1",
                None,
                scope,
                plugin_name,
                status,
                "2026-01-01T00:00:00+00:00",
                None,
                None,
            ),
        )
    return conn


class TestFormatEvalSummary:
    def test_all_passed_reports_completed(self) -> None:
        conn = _eval_db(
            [
                ("turn", "action_counts", "passed"),
                ("run", "feed_coverage", "passed"),
            ]
        )
        result = format_eval_summary("run-1", conn)
        assert "all completed" in result
        assert "Run-scope: feed_coverage=passed" in result

    def test_failed_reports_failed_plugins(self) -> None:
        conn = _eval_db([("run", "action_counts", "failed")])
        result = format_eval_summary("run-1", conn)
        assert "failed: action_counts" in result
        assert "all completed" not in result

    def test_non_terminal_status_reports_incomplete(self) -> None:
        conn = _eval_db(
            [
                ("turn", "action_counts", "passed"),
                ("run", "feed_coverage", "running"),
            ]
        )
        result = format_eval_summary("run-1", conn)
        assert "incomplete: feed_coverage=running" in result
        assert "all completed" not in result
        assert "Run-scope: feed_coverage=running" in result
