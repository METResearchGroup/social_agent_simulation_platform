"""Unit tests for personalized memory diff builders."""

from __future__ import annotations

from simulation_v2.memory.personalized import (
    append_personalized,
    build_personalized_diff_content,
)
from tests.simulation_v2.db import factories


class TestBuildPersonalizedDiffContent:
    def test_write_post(self) -> None:
        action = factories.ProposedActionRecordFactory.create(
            user_id="u1",
            action_type="write_post",
            target_content="hello world",
            record_kind="validated",
        )
        content = build_personalized_diff_content(1, [action])
        assert content == 'Turn 1: posted "hello world"'

    def test_empty_returns_none(self) -> None:
        action = factories.ProposedActionRecordFactory.create(
            user_id="u1",
            action_type="like_post",
            target_id="p1",
            record_kind="validated",
        )
        assert build_personalized_diff_content(1, [action]) is None


class TestAppendPersonalized:
    def test_appends_with_newline_when_existing(self) -> None:
        assert append_personalized(
            'Turn 0: posted "seed"',
            'Turn 1: posted "hello world"',
        ) == ('Turn 0: posted "seed"\nTurn 1: posted "hello world"')
