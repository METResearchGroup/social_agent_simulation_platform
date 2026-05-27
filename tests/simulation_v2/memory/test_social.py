"""Unit tests for social memory diff builders."""

from __future__ import annotations

from simulation_v2.memory.social import append_social, build_social_diff_content
from tests.simulation_v2.db import factories


class TestBuildSocialDiffContent:
    def test_follow_user(self) -> None:
        action = factories.ProposedActionRecordFactory.create(
            user_id="u1",
            action_type="follow_user",
            target_id="u2",
            record_kind="validated",
        )
        content = build_social_diff_content(1, [action])
        assert content == "Turn 1: followed u2"

    def test_no_follow_returns_none(self) -> None:
        action = factories.ProposedActionRecordFactory.create(
            user_id="u1",
            action_type="like_post",
            target_id="p1",
            record_kind="validated",
        )
        assert build_social_diff_content(1, [action]) is None


class TestAppendSocial:
    def test_appends_with_newline_when_existing(self) -> None:
        assert append_social("Turn 0: followed u0", "Turn 1: followed u2") == (
            "Turn 0: followed u0\nTurn 1: followed u2"
        )
