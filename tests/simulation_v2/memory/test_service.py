"""Unit tests for memory service orchestration."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from simulation_v2.config import LocalSimulationConfig
from simulation_v2.memory.service import (
    apply_memory_diff,
    build_memory_diffs,
    fetch_memory_for_prompt,
)
from simulation_v2.worker.state import TurnStateSnapshot
from tests.simulation_v2.db import factories

FIXED_TS = "2026-01-01T00:00:00.000000+00:00"
RUN_ID = "run-1"
TURN_ID = "turn-1"


def _snapshot(*, turn_number: int = 1) -> TurnStateSnapshot:
    return TurnStateSnapshot(
        run_id=RUN_ID,
        turn_id=TURN_ID,
        turn_number=turn_number,
        config=LocalSimulationConfig.default(),
        users={},
        posts={},
        likes=[],
        follows=[],
        comments=[],
        agent_memories={},
        prior_generated_feeds=[],
    )


class TestFetchMemoryForPrompt:
    def test_formats_all_sections(self) -> None:
        memory = factories.AgentMemoryRecordFactory.create(
            episodic="ep1",
            personalized="pers1",
            social="soc1",
        )
        text = fetch_memory_for_prompt(memory)
        assert "Episodic memory" in text
        assert "ep1" in text
        assert "pers1" in text
        assert "soc1" in text

    def test_none_memory_uses_empty_strings(self) -> None:
        text = fetch_memory_for_prompt(None)
        assert "Episodic memory" in text
        assert "Personalized profile memory" in text
        assert "Social relationships memory" in text


class TestBuildMemoryDiffs:
    @patch("simulation_v2.memory.service.get_current_timestamp", return_value=FIXED_TS)
    def test_mixed_actions_emit_up_to_three_diffs(
        self, mock_timestamp: MagicMock
    ) -> None:
        like = factories.ProposedActionRecordFactory.create(
            run_id=RUN_ID,
            turn_id=TURN_ID,
            user_id="u1",
            action_type="like_post",
            target_id="p2",
            record_kind="validated",
        )
        write = factories.ProposedActionRecordFactory.create(
            run_id=RUN_ID,
            turn_id=TURN_ID,
            user_id="u1",
            action_type="write_post",
            target_content="hello world",
            record_kind="validated",
        )
        follow = factories.ProposedActionRecordFactory.create(
            run_id=RUN_ID,
            turn_id=TURN_ID,
            user_id="u1",
            action_type="follow_user",
            target_id="u2",
            record_kind="validated",
        )
        diffs = build_memory_diffs([like, write, follow], _snapshot())
        assert len(diffs) == 3
        types = {diff.memory_type for diff in diffs}
        assert types == {"episodic", "personalized", "social"}
        episodic = next(d for d in diffs if d.memory_type == "episodic")
        assert episodic.content == (
            'Turn 1: liked post p2; wrote post "hello world"; followed user u2'
        )
        assert episodic.run_id == RUN_ID
        assert episodic.turn_id == TURN_ID
        assert episodic.user_id == "u1"
        assert episodic.created_at == FIXED_TS

    def test_no_actions_returns_empty(self) -> None:
        assert build_memory_diffs([], _snapshot()) == []


class TestApplyMemoryDiff:
    @patch("simulation_v2.memory.service.get_current_timestamp", return_value=FIXED_TS)
    def test_appends_episodic_content(self, mock_timestamp: MagicMock) -> None:
        current = factories.AgentMemoryRecordFactory.create(
            episodic="Turn 0: seed",
            updated_at="old-ts",
        )
        diff = factories.MemoryDiffRecordFactory.create(
            run_id=current.run_id,
            user_id=current.user_id,
            memory_type="episodic",
            content="Turn 1: liked post p1",
        )
        updated = apply_memory_diff(current, diff)
        assert updated.episodic == "Turn 0: seed\nTurn 1: liked post p1"
        assert updated.updated_at == FIXED_TS
        assert updated.personalized == current.personalized
        assert updated.social == current.social
