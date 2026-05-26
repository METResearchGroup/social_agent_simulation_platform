"""Unit tests for action/generation Pydantic models."""

from __future__ import annotations

from simulation_v2.db.models import (
    GenerationRecord,
    LlmProposedActionRecord,
    ProposedActionRecord,
)
from simulation_v2.time import get_current_timestamp


class TestActionModels:
    def test_generation_record_round_trip(self) -> None:
        record = GenerationRecord(
            generation_id="gen-1",
            run_id="run-1",
            turn_id="turn-1",
            user_id="u1",
            action_type="like",
            parsed_response_json={"post_ids": ["p1"]},
            raw_response_json={"text": "ok"},
            status="completed",
            created_at=get_current_timestamp(),
        )

        assert GenerationRecord.model_validate(record.model_dump()) == record

    def test_llm_proposed_action_record_round_trip(self) -> None:
        record = LlmProposedActionRecord(
            llm_proposed_action_id="lpa-1",
            generation_id="gen-1",
            run_id="run-1",
            turn_id="turn-1",
            user_id="u1",
            action_type="like",
            target_type="post",
            target_id="p1",
            created_at=get_current_timestamp(),
        )

        assert LlmProposedActionRecord.model_validate(record.model_dump()) == record

    def test_proposed_action_record_round_trip(self) -> None:
        record = ProposedActionRecord(
            action_id="a1",
            record_kind="rejected",
            generation_id="gen-1",
            run_id="run-1",
            turn_id="turn-1",
            user_id="u1",
            action_type="like",
            rejection_stage="business_rules",
            filter_reason="duplicate",
            created_at=get_current_timestamp(),
        )

        assert ProposedActionRecord.model_validate(record.model_dump()) == record
