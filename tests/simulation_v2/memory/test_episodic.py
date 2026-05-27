"""Unit tests for episodic memory diff builders."""

from __future__ import annotations

from simulation_v2.memory.episodic import append_episodic, build_episodic_diff_content
from tests.simulation_v2.db import factories


class TestBuildEpisodicDiffContent:
    def test_like_only(self) -> None:
        action = factories.ProposedActionRecordFactory.create(
            user_id="u1",
            action_type="like_post",
            target_id="p2",
            record_kind="validated",
        )
        content = build_episodic_diff_content(1, [action])
        assert content == "Turn 1: liked post p2"

    def test_multi_action(self) -> None:
        like = factories.ProposedActionRecordFactory.create(
            user_id="u1",
            action_type="like_post",
            target_id="p2",
            record_kind="validated",
        )
        write = factories.ProposedActionRecordFactory.create(
            user_id="u1",
            action_type="write_post",
            target_content="hello world",
            record_kind="validated",
        )
        follow = factories.ProposedActionRecordFactory.create(
            user_id="u1",
            action_type="follow_user",
            target_id="u2",
            record_kind="validated",
        )
        comment = factories.ProposedActionRecordFactory.create(
            user_id="u1",
            action_type="comment_on_post",
            target_id="p1",
            target_content="nice post",
            record_kind="validated",
        )
        content = build_episodic_diff_content(1, [like, write, follow, comment])
        assert content == (
            'Turn 1: liked post p2; wrote post "hello world"; '
            'followed user u2; commented on p1 "nice post"'
        )

    def test_empty_input_returns_none(self) -> None:
        assert build_episodic_diff_content(1, []) is None


class TestAppendEpisodic:
    def test_appends_with_newline_when_existing(self) -> None:
        assert append_episodic("Turn 0: seed", "Turn 1: liked post p1") == (
            "Turn 0: seed\nTurn 1: liked post p1"
        )

    def test_returns_segment_when_no_existing(self) -> None:
        assert append_episodic(None, "Turn 1: liked post p1") == "Turn 1: liked post p1"
