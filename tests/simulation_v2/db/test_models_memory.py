"""Unit tests for memory Pydantic models."""

from __future__ import annotations

from simulation_v2.db.models import AgentMemoryRecord, MemoryDiffRecord
from simulation_v2.time import get_current_timestamp


class TestMemoryModels:
    def test_agent_memory_record_round_trip(self) -> None:
        record = AgentMemoryRecord(
            run_id="run-1",
            user_id="u1",
            preferences_json={"theme": "dark"},
            episodic="remembered event",
            personalized="profile note",
            social="friend context",
            updated_at=get_current_timestamp(),
        )

        assert AgentMemoryRecord.model_validate(record.model_dump()) == record

    def test_memory_diff_record_round_trip(self) -> None:
        record = MemoryDiffRecord(
            memory_diff_id="md1",
            run_id="run-1",
            turn_id="turn-1",
            user_id="u1",
            memory_type="social",
            content="updated relationship",
            created_at=get_current_timestamp(),
        )

        assert MemoryDiffRecord.model_validate(record.model_dump()) == record
