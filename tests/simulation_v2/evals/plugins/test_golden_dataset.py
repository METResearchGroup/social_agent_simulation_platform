"""Tests for golden_dataset eval plugin."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

import simulation_v2.evals  # noqa: F401 — registers builtins
from simulation_v2.config import EvalConfig, LocalSimulationConfig
from simulation_v2.db.connection import transaction
from simulation_v2.db.database import SimulationDatabase
from simulation_v2.evals.interfaces import EvalContext
from simulation_v2.evals.plugins.golden_dataset import GoldenDatasetPlugin
from simulation_v2.evals.runner import run_turn_evals
from tests.simulation_v2.db import factories


@dataclass(frozen=True)
class GoldenEvalFixture:
    db_path: Path
    run_id: str
    turn_id: str
    turn_number: int


def _insert_run_turn(conn, db: SimulationDatabase, run, turn) -> None:
    db.repos.insert_run(run, conn)
    db.repos.insert_turn(turn, conn)


def _build_context(fixture: GoldenEvalFixture, conn, repos) -> EvalContext:
    return EvalContext(
        repos=repos,
        conn=conn,
        run_id=fixture.run_id,
        config=LocalSimulationConfig.default(),
        scope="turn",
        turn_id=fixture.turn_id,
        turn_number=fixture.turn_number,
    )


def _metric(
    result,
    metric_name: str,
    *,
    case_id: str | None = None,
    label_type: str | None = None,
):
    for metric in result.metrics:
        if metric.metric_name != metric_name:
            continue
        metadata = metric.metadata_json or {}
        if case_id is not None and metadata.get("case_id") != case_id:
            continue
        if label_type is not None and metadata.get("label_type") != label_type:
            continue
        if metadata.get("aggregate") == "macro":
            continue
        return metric
    raise AssertionError(
        f"metric {metric_name!r} not found for case_id={case_id!r} label_type={label_type!r}"
    )


def seed_partial_likes_db(db_path: Path) -> GoldenEvalFixture:
    db = SimulationDatabase(db_path)
    db.initialize()

    run = factories.RunRecordFactory.create()
    turn = factories.TurnRecordFactory.create(
        run_id=run.run_id, turn_number=1, status="completed"
    )
    user = factories.UserRecordFactory.create(
        run_id=run.run_id, user_id="golden-user-like"
    )
    gen = factories.GenerationRecordFactory.create(
        run_id=run.run_id,
        turn_id=turn.turn_id,
        user_id=user.user_id,
        action_type="like_post",
        status="completed",
    )
    proposed = factories.ProposedActionRecordFactory.create(
        run_id=run.run_id,
        turn_id=turn.turn_id,
        user_id=user.user_id,
        action_type="like_post",
        record_kind="validated",
        generation_id=gen.generation_id,
        target_id="golden-post-a",
    )

    with transaction(db_path) as conn:
        _insert_run_turn(conn, db, run, turn)
        db.repos.insert_user(user, conn)
        db.repos.insert_generation(gen, conn)
        db.repos.insert_proposed_action(proposed, conn)

    return GoldenEvalFixture(
        db_path=db_path,
        run_id=run.run_id,
        turn_id=turn.turn_id,
        turn_number=turn.turn_number,
    )


def seed_perfect_follow_db(db_path: Path) -> GoldenEvalFixture:
    db = SimulationDatabase(db_path)
    db.initialize()

    run = factories.RunRecordFactory.create()
    turn = factories.TurnRecordFactory.create(
        run_id=run.run_id, turn_number=1, status="completed"
    )
    user = factories.UserRecordFactory.create(
        run_id=run.run_id, user_id="golden-user-follow"
    )
    target = factories.UserRecordFactory.create(
        run_id=run.run_id, user_id="golden-target-user"
    )
    gen = factories.GenerationRecordFactory.create(
        run_id=run.run_id,
        turn_id=turn.turn_id,
        user_id=user.user_id,
        action_type="follow_user",
        status="completed",
    )
    proposed = factories.ProposedActionRecordFactory.create(
        run_id=run.run_id,
        turn_id=turn.turn_id,
        user_id=user.user_id,
        action_type="follow_user",
        record_kind="validated",
        generation_id=gen.generation_id,
        target_id=target.user_id,
    )

    with transaction(db_path) as conn:
        _insert_run_turn(conn, db, run, turn)
        db.repos.insert_user(user, conn)
        db.repos.insert_user(target, conn)
        db.repos.insert_generation(gen, conn)
        db.repos.insert_proposed_action(proposed, conn)

    return GoldenEvalFixture(
        db_path=db_path,
        run_id=run.run_id,
        turn_id=turn.turn_id,
        turn_number=turn.turn_number,
    )


def seed_write_topic_db(db_path: Path) -> GoldenEvalFixture:
    db = SimulationDatabase(db_path)
    db.initialize()

    run = factories.RunRecordFactory.create()
    turn = factories.TurnRecordFactory.create(
        run_id=run.run_id, turn_number=1, status="completed"
    )
    user = factories.UserRecordFactory.create(
        run_id=run.run_id, user_id="golden-user-write"
    )
    gen = factories.GenerationRecordFactory.create(
        run_id=run.run_id,
        turn_id=turn.turn_id,
        user_id=user.user_id,
        action_type="write_post",
        status="completed",
    )
    proposed = factories.ProposedActionRecordFactory.create(
        run_id=run.run_id,
        turn_id=turn.turn_id,
        user_id=user.user_id,
        action_type="write_post",
        record_kind="validated",
        generation_id=gen.generation_id,
        target_content="Renewable Energy",
    )

    with transaction(db_path) as conn:
        _insert_run_turn(conn, db, run, turn)
        db.repos.insert_user(user, conn)
        db.repos.insert_generation(gen, conn)
        db.repos.insert_proposed_action(proposed, conn)

    return GoldenEvalFixture(
        db_path=db_path,
        run_id=run.run_id,
        turn_id=turn.turn_id,
        turn_number=turn.turn_number,
    )


def seed_negative_like_db(db_path: Path, fixture_path: Path) -> GoldenEvalFixture:
    db = SimulationDatabase(db_path)
    db.initialize()

    fixture_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "cases": [
                    {
                        "case_id": "negative_likes",
                        "user_id": "golden-user-negative",
                        "expected_like_post_ids": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    run = factories.RunRecordFactory.create()
    turn = factories.TurnRecordFactory.create(
        run_id=run.run_id, turn_number=1, status="completed"
    )
    user = factories.UserRecordFactory.create(
        run_id=run.run_id, user_id="golden-user-negative"
    )
    gen = factories.GenerationRecordFactory.create(
        run_id=run.run_id,
        turn_id=turn.turn_id,
        user_id=user.user_id,
        action_type="like_post",
        status="completed",
    )
    proposed = factories.ProposedActionRecordFactory.create(
        run_id=run.run_id,
        turn_id=turn.turn_id,
        user_id=user.user_id,
        action_type="like_post",
        record_kind="validated",
        generation_id=gen.generation_id,
        target_id="unexpected-post",
    )

    with transaction(db_path) as conn:
        _insert_run_turn(conn, db, run, turn)
        db.repos.insert_user(user, conn)
        db.repos.insert_generation(gen, conn)
        db.repos.insert_proposed_action(proposed, conn)

    return GoldenEvalFixture(
        db_path=db_path,
        run_id=run.run_id,
        turn_id=turn.turn_id,
        turn_number=turn.turn_number,
    )


class TestGoldenDatasetPlugin:
    def test_partial_likes_recall_below_one_precision_one(self, tmp_path: Path) -> None:
        fixture = seed_partial_likes_db(tmp_path / "partial_likes.sqlite3")
        db = SimulationDatabase(fixture.db_path)
        with transaction(fixture.db_path) as conn:
            result = GoldenDatasetPlugin().run(_build_context(fixture, conn, db.repos))

        assert result.status == "passed"
        assert _metric(
            result, "precision", case_id="partial_likes", label_type="like"
        ).metric_value == pytest.approx(1.0)
        assert _metric(
            result, "recall", case_id="partial_likes", label_type="like"
        ).metric_value == pytest.approx(0.5)
        assert any(
            "skipped label_type=follow" in warning for warning in result.warnings
        )
        assert any(
            "skipped label_type=write_topic" in warning for warning in result.warnings
        )

    def test_partial_follows_perfect_f1(self, tmp_path: Path) -> None:
        fixture = seed_perfect_follow_db(tmp_path / "follows.sqlite3")
        db = SimulationDatabase(fixture.db_path)
        with transaction(fixture.db_path) as conn:
            result = GoldenDatasetPlugin().run(_build_context(fixture, conn, db.repos))

        assert _metric(
            result, "f1", case_id="partial_follows", label_type="follow"
        ).metric_value == pytest.approx(1.0)

    def test_write_topic_case_insensitive_match(self, tmp_path: Path) -> None:
        fixture = seed_write_topic_db(tmp_path / "write_topic.sqlite3")
        db = SimulationDatabase(fixture.db_path)
        with transaction(fixture.db_path) as conn:
            result = GoldenDatasetPlugin().run(_build_context(fixture, conn, db.repos))

        assert _metric(
            result, "f1", case_id="partial_write_topic", label_type="write_topic"
        ).metric_value == pytest.approx(1.0)

    def test_absent_labels_skipped_with_warnings(self, tmp_path: Path) -> None:
        fixture = seed_partial_likes_db(tmp_path / "absent_labels.sqlite3")
        db = SimulationDatabase(fixture.db_path)
        with transaction(fixture.db_path) as conn:
            result = GoldenDatasetPlugin().run(_build_context(fixture, conn, db.repos))

        follow_metrics = [
            m
            for m in result.metrics
            if (m.metadata_json or {}).get("label_type") == "follow"
            and (m.metadata_json or {}).get("case_id") == "partial_likes"
        ]
        write_metrics = [
            m
            for m in result.metrics
            if (m.metadata_json or {}).get("label_type") == "write_topic"
            and (m.metadata_json or {}).get("case_id") == "partial_likes"
        ]
        assert follow_metrics == []
        assert write_metrics == []
        assert any("skipped label_type=follow" in w for w in result.warnings)
        assert any("skipped label_type=write_topic" in w for w in result.warnings)

    def test_negative_label_zero_precision(self, tmp_path: Path) -> None:
        fixture_path = tmp_path / "negative_fixture.json"
        fixture = seed_negative_like_db(
            tmp_path / "negative_like.sqlite3", fixture_path
        )
        db = SimulationDatabase(fixture.db_path)
        with transaction(fixture.db_path) as conn:
            result = GoldenDatasetPlugin(fixture_path=fixture_path).run(
                _build_context(fixture, conn, db.repos)
            )

        assert _metric(
            result, "precision", case_id="negative_likes", label_type="like"
        ).metric_value == pytest.approx(0.0)
        assert _metric(
            result, "f1", case_id="negative_likes", label_type="like"
        ).metric_value == pytest.approx(0.0)

    def test_runner_persists_golden_dataset_metrics(self, tmp_path: Path) -> None:
        fixture = seed_partial_likes_db(tmp_path / "runner.sqlite3")
        db = SimulationDatabase(fixture.db_path)
        config = LocalSimulationConfig.default().model_copy(
            update={
                "evals": EvalConfig(
                    enabled=True,
                    fail_run_on_error=False,
                    turn_plugins=["golden_dataset"],
                    run_plugins=[],
                )
            }
        )

        with transaction(fixture.db_path) as conn:
            summaries = run_turn_evals(
                fixture.run_id,
                fixture.turn_id,
                fixture.turn_number,
                config,
                db.repos,
                conn,
            )

        assert len(summaries) == 1
        assert summaries[0].plugin_name == "golden_dataset"

        with transaction(fixture.db_path) as conn:
            row = conn.execute("SELECT COUNT(*) AS count FROM eval_runs").fetchone()
            metric_row = conn.execute(
                "SELECT COUNT(*) AS count FROM eval_metrics"
            ).fetchone()

        assert int(row["count"]) == 1
        assert int(metric_row["count"]) > 0
