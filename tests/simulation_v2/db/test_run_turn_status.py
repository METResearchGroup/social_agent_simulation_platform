"""Run and turn status transition and query tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from simulation_v2.db.connection import transaction
from simulation_v2.db.database import SimulationDatabase
from simulation_v2.db.errors import (
    InvalidStatusTransitionError,
    RunNotFoundError,
)
from tests.simulation_v2.db import factories

FIXED_TS = "2026-05-26T12:00:00.000000+00:00"
FIXED_TS_2 = "2026-05-26T13:00:00.000000+00:00"


@pytest.fixture
def db(tmp_path: Path) -> SimulationDatabase:
    database = SimulationDatabase(tmp_path / "test.sqlite3")
    database.initialize()
    return database


class TestRunStatusTransitions:
    def test_insert_run_defaults_to_queued(self, db: SimulationDatabase) -> None:
        run = factories.RunRecordFactory.create()
        with transaction(db._db_path) as conn:
            db.repos.insert_run(run, conn)
            loaded = db.repos.get_run(run.run_id, conn)

        assert loaded is not None
        assert loaded.status == "queued"
        assert loaded.started_at is None
        assert loaded.finished_at is None

    def test_queued_to_running_sets_started_at(self, db: SimulationDatabase) -> None:
        run = factories.RunRecordFactory.create()
        with transaction(db._db_path) as conn:
            db.repos.insert_run(run, conn)
            updated = db.repos.update_run_status(
                run.run_id, "running", conn, timestamp=FIXED_TS
            )

        assert updated.status == "running"
        assert updated.started_at == FIXED_TS
        assert updated.finished_at is None

    def test_running_to_completed_sets_finished_at_clears_error(
        self, db: SimulationDatabase
    ) -> None:
        run = factories.RunRecordFactory.create()
        with transaction(db._db_path) as conn:
            db.repos.insert_run(run, conn)
            db.repos.update_run_status(run.run_id, "running", conn, timestamp=FIXED_TS)
            updated = db.repos.update_run_status(
                run.run_id, "completed", conn, timestamp=FIXED_TS_2
            )

        assert updated.status == "completed"
        assert updated.started_at == FIXED_TS
        assert updated.finished_at == FIXED_TS_2
        assert updated.error is None

    def test_running_to_failed_persists_error_and_finished_at(
        self, db: SimulationDatabase
    ) -> None:
        run = factories.RunRecordFactory.create()
        with transaction(db._db_path) as conn:
            db.repos.insert_run(run, conn)
            db.repos.update_run_status(run.run_id, "running", conn, timestamp=FIXED_TS)
            updated = db.repos.update_run_status(
                run.run_id,
                "failed",
                conn,
                error="worker crashed",
                timestamp=FIXED_TS_2,
            )

        assert updated.status == "failed"
        assert updated.finished_at == FIXED_TS_2
        assert updated.error == "worker crashed"

    def test_failed_requires_error_message(self, db: SimulationDatabase) -> None:
        run = factories.RunRecordFactory.create()
        with transaction(db._db_path) as conn:
            db.repos.insert_run(run, conn)
            db.repos.update_run_status(run.run_id, "running", conn, timestamp=FIXED_TS)
            with pytest.raises(ValueError, match="error"):
                db.repos.update_run_status(
                    run.run_id, "failed", conn, timestamp=FIXED_TS_2
                )

    def test_idempotent_completed_update(self, db: SimulationDatabase) -> None:
        run = factories.RunRecordFactory.create()
        with transaction(db._db_path) as conn:
            db.repos.insert_run(run, conn)
            db.repos.update_run_status(run.run_id, "running", conn, timestamp=FIXED_TS)
            first = db.repos.update_run_status(
                run.run_id, "completed", conn, timestamp=FIXED_TS_2
            )
            second = db.repos.update_run_status(
                run.run_id,
                "completed",
                conn,
                timestamp="2026-05-26T14:00:00.000000+00:00",
            )

        assert first == second
        assert second.finished_at == FIXED_TS_2

    def test_rejects_completed_to_running(self, db: SimulationDatabase) -> None:
        run = factories.RunRecordFactory.create()
        with transaction(db._db_path) as conn:
            db.repos.insert_run(run, conn)
            db.repos.update_run_status(run.run_id, "running", conn, timestamp=FIXED_TS)
            db.repos.update_run_status(
                run.run_id, "completed", conn, timestamp=FIXED_TS_2
            )
            with pytest.raises(InvalidStatusTransitionError):
                db.repos.update_run_status(
                    run.run_id, "running", conn, timestamp=FIXED_TS_2
                )

    def test_update_missing_run_raises_run_not_found(
        self, db: SimulationDatabase
    ) -> None:
        with transaction(db._db_path) as conn:
            with pytest.raises(RunNotFoundError):
                db.repos.update_run_status(
                    "run_missing", "running", conn, timestamp=FIXED_TS
                )


class TestTurnStatusTransitions:
    def test_insert_turn_defaults_to_pending(self, db: SimulationDatabase) -> None:
        run = factories.RunRecordFactory.create()
        turn = factories.TurnRecordFactory.create(run_id=run.run_id)
        with transaction(db._db_path) as conn:
            db.repos.insert_run(run, conn)
            db.repos.insert_turn(turn, conn)
            loaded = db.repos.get_turn(turn.turn_id, conn)

        assert loaded is not None
        assert loaded.status == "pending"
        assert loaded.started_at is None
        assert loaded.finished_at is None

    def test_pending_to_running_sets_started_at(self, db: SimulationDatabase) -> None:
        run = factories.RunRecordFactory.create()
        turn = factories.TurnRecordFactory.create(run_id=run.run_id)
        with transaction(db._db_path) as conn:
            db.repos.insert_run(run, conn)
            db.repos.insert_turn(turn, conn)
            updated = db.repos.update_turn_status(
                turn.turn_id, "running", conn, timestamp=FIXED_TS
            )

        assert updated.status == "running"
        assert updated.started_at == FIXED_TS

    def test_running_to_completed(self, db: SimulationDatabase) -> None:
        run = factories.RunRecordFactory.create()
        turn = factories.TurnRecordFactory.create(run_id=run.run_id)
        with transaction(db._db_path) as conn:
            db.repos.insert_run(run, conn)
            db.repos.insert_turn(turn, conn)
            db.repos.update_turn_status(
                turn.turn_id, "running", conn, timestamp=FIXED_TS
            )
            updated = db.repos.update_turn_status(
                turn.turn_id, "completed", conn, timestamp=FIXED_TS_2
            )

        assert updated.status == "completed"
        assert updated.finished_at == FIXED_TS_2
        assert updated.error is None

    def test_running_to_failed_persists_error(self, db: SimulationDatabase) -> None:
        run = factories.RunRecordFactory.create()
        turn = factories.TurnRecordFactory.create(run_id=run.run_id)
        with transaction(db._db_path) as conn:
            db.repos.insert_run(run, conn)
            db.repos.insert_turn(turn, conn)
            db.repos.update_turn_status(
                turn.turn_id, "running", conn, timestamp=FIXED_TS
            )
            updated = db.repos.update_turn_status(
                turn.turn_id,
                "failed",
                conn,
                error="turn error",
                timestamp=FIXED_TS_2,
            )

        assert updated.status == "failed"
        assert updated.error == "turn error"
        assert updated.finished_at == FIXED_TS_2

    def test_rejects_completed_to_running(self, db: SimulationDatabase) -> None:
        run = factories.RunRecordFactory.create()
        turn = factories.TurnRecordFactory.create(run_id=run.run_id)
        with transaction(db._db_path) as conn:
            db.repos.insert_run(run, conn)
            db.repos.insert_turn(turn, conn)
            db.repos.update_turn_status(
                turn.turn_id, "running", conn, timestamp=FIXED_TS
            )
            db.repos.update_turn_status(
                turn.turn_id, "completed", conn, timestamp=FIXED_TS_2
            )
            with pytest.raises(InvalidStatusTransitionError):
                db.repos.update_turn_status(
                    turn.turn_id, "running", conn, timestamp=FIXED_TS_2
                )


class TestTurnQueries:
    def test_list_turns_for_run_ordered_by_turn_number(
        self, db: SimulationDatabase
    ) -> None:
        run = factories.RunRecordFactory.create()
        turn3 = factories.TurnRecordFactory.create(run_id=run.run_id, turn_number=3)
        turn1 = factories.TurnRecordFactory.create(run_id=run.run_id, turn_number=1)
        turn2 = factories.TurnRecordFactory.create(run_id=run.run_id, turn_number=2)
        with transaction(db._db_path) as conn:
            db.repos.insert_run(run, conn)
            for turn in (turn3, turn1, turn2):
                db.repos.insert_turn(turn, conn)
            loaded = db.repos.list_turns_for_run(run.run_id, conn)

        assert [t.turn_number for t in loaded] == [1, 2, 3]

    def test_get_turn_by_run_and_number(self, db: SimulationDatabase) -> None:
        run = factories.RunRecordFactory.create()
        turn = factories.TurnRecordFactory.create(run_id=run.run_id, turn_number=2)
        with transaction(db._db_path) as conn:
            db.repos.insert_run(run, conn)
            db.repos.insert_turn(turn, conn)
            loaded = db.repos.get_turn_by_run_and_number(run.run_id, 2, conn)

        assert loaded is not None
        assert loaded.turn_id == turn.turn_id

    def test_get_turn_by_run_and_number_returns_none_when_missing(
        self, db: SimulationDatabase
    ) -> None:
        run = factories.RunRecordFactory.create()
        with transaction(db._db_path) as conn:
            db.repos.insert_run(run, conn)
            loaded = db.repos.get_turn_by_run_and_number(run.run_id, 99, conn)

        assert loaded is None

    def test_completed_turn_detectable_for_retry(self, db: SimulationDatabase) -> None:
        run = factories.RunRecordFactory.create()
        turn1 = factories.TurnRecordFactory.create(run_id=run.run_id, turn_number=1)
        turn2 = factories.TurnRecordFactory.create(run_id=run.run_id, turn_number=2)
        with transaction(db._db_path) as conn:
            db.repos.insert_run(run, conn)
            db.repos.insert_turn(turn1, conn)
            db.repos.insert_turn(turn2, conn)
            db.repos.update_turn_status(
                turn1.turn_id, "running", conn, timestamp=FIXED_TS
            )
            db.repos.update_turn_status(
                turn1.turn_id, "completed", conn, timestamp=FIXED_TS_2
            )
            loaded1 = db.repos.get_turn_by_run_and_number(run.run_id, 1, conn)
            loaded2 = db.repos.get_turn_by_run_and_number(run.run_id, 2, conn)

        assert loaded1 is not None
        assert loaded1.status == "completed"
        assert loaded2 is not None
        assert loaded2.status == "pending"
