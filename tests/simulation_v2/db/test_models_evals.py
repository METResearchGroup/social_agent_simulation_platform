"""Unit tests for eval Pydantic models."""

from __future__ import annotations

from simulation_v2.db.models import EvalMetricRecord, EvalRunRecord
from simulation_v2.time import get_current_timestamp


class TestEvalModels:
    def test_eval_run_record_round_trip(self) -> None:
        record = EvalRunRecord(
            eval_run_id="er-1",
            run_id="run-1",
            turn_id="turn-1",
            scope="turn",
            plugin_name="action_counts",
            status="completed",
            created_at=get_current_timestamp(),
        )

        assert EvalRunRecord.model_validate(record.model_dump()) == record

    def test_eval_metric_record_round_trip(self) -> None:
        record = EvalMetricRecord(
            eval_metric_id="em-1",
            eval_run_id="er-1",
            run_id="run-1",
            turn_id="turn-1",
            plugin_name="action_counts",
            metric_name="likes",
            metric_value=3.0,
            metadata_json={"unit": "count"},
            created_at=get_current_timestamp(),
        )

        assert EvalMetricRecord.model_validate(record.model_dump()) == record
