"""Unit tests for run and turn Pydantic models."""

from __future__ import annotations

from simulation_v2.config import LocalSimulationConfig
from simulation_v2.db.models import RunRecord, TurnRecord
from simulation_v2.time import get_current_timestamp


class TestRunRecord:
    def test_validates_sample_payload(self) -> None:
        config = LocalSimulationConfig.default()
        record = RunRecord(
            run_id="run-1",
            status="queued",
            config_json=config.model_dump(mode="json"),
            created_at=get_current_timestamp(),
        )

        assert record.run_id == "run-1"
        assert record.status == "queued"
        assert record.config_json["total_turns"] == 3

    def test_round_trip_model_dump(self) -> None:
        record = RunRecord(
            run_id="run-1",
            status="running",
            config_json={"total_turns": 2},
            seed_metadata_json={"seed": "fixture"},
            created_at=get_current_timestamp(),
            started_at=get_current_timestamp(),
        )

        restored = RunRecord.model_validate(record.model_dump())

        assert restored == record


class TestTurnRecord:
    def test_validates_sample_payload(self) -> None:
        record = TurnRecord(
            turn_id="turn-1",
            run_id="run-1",
            turn_number=1,
            status="pending",
            created_at=get_current_timestamp(),
        )

        assert record.turn_number == 1

    def test_round_trip_model_dump(self) -> None:
        record = TurnRecord(
            turn_id="turn-1",
            run_id="run-1",
            turn_number=2,
            status="completed",
            created_at=get_current_timestamp(),
            finished_at=get_current_timestamp(),
        )

        restored = TurnRecord.model_validate(record.model_dump())

        assert restored == record
