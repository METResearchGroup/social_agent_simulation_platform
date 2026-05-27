"""Unit tests for build_pending_turn_diffs."""

from __future__ import annotations

import pytest

from simulation_v2.actions.executor import build_pending_turn_diffs
from simulation_v2.config import LocalSimulationConfig
from simulation_v2.worker.state import TurnStateSnapshot
from tests.simulation_v2.db import factories

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


class TestBuildPendingTurnDiffs:
    def test_like_post_maps_to_like_record(self) -> None:
        action = factories.ProposedActionRecordFactory.create(
            run_id=RUN_ID,
            turn_id=TURN_ID,
            user_id="u1",
            action_type="like_post",
            target_id="p2",
            record_kind="validated",
        )
        diffs = build_pending_turn_diffs([action], _snapshot())
        assert len(diffs.likes) == 1
        like = diffs.likes[0]
        assert like.author_id == "u1"
        assert like.post_id == "p2"
        assert like.run_id == RUN_ID
        assert like.created_at_turn == 1
        assert like.metadata_json == {
            "proposed_action_id": action.action_id,
            "generation_id": action.generation_id,
        }

    def test_follow_user_maps_to_follow_record(self) -> None:
        action = factories.ProposedActionRecordFactory.create(
            run_id=RUN_ID,
            user_id="u1",
            action_type="follow_user",
            target_id="u2",
            record_kind="validated",
        )
        diffs = build_pending_turn_diffs([action], _snapshot())
        assert len(diffs.follows) == 1
        follow = diffs.follows[0]
        assert follow.follower_id == "u1"
        assert follow.followee_id == "u2"
        assert follow.created_at_turn == 1

    def test_write_post_maps_to_post_record_with_new_id(self) -> None:
        action = factories.ProposedActionRecordFactory.create(
            run_id=RUN_ID,
            user_id="u1",
            action_type="write_post",
            target_id=None,
            target_content="hello world",
            record_kind="validated",
        )
        diffs = build_pending_turn_diffs([action], _snapshot())
        assert len(diffs.posts) == 1
        post = diffs.posts[0]
        assert post.author_id == "u1"
        assert post.content == "hello world"
        assert post.post_id
        assert post.created_at_turn == 1

    def test_comment_on_post_maps_to_comment_record(self) -> None:
        action = factories.ProposedActionRecordFactory.create(
            run_id=RUN_ID,
            user_id="u1",
            action_type="comment_on_post",
            target_id="p1",
            target_content="nice post",
            record_kind="validated",
        )
        diffs = build_pending_turn_diffs([action], _snapshot())
        assert len(diffs.comments) == 1
        comment = diffs.comments[0]
        assert comment.author_id == "u1"
        assert comment.parent_post_id == "p1"
        assert comment.content == "nice post"
        assert comment.created_at_turn == 1

    def test_preserves_input_order_for_multiple_likes(self) -> None:
        like_a = factories.ProposedActionRecordFactory.create(
            run_id=RUN_ID,
            user_id="u1",
            action_type="like_post",
            target_id="p1",
            record_kind="validated",
        )
        like_b = factories.ProposedActionRecordFactory.create(
            run_id=RUN_ID,
            user_id="u1",
            action_type="like_post",
            target_id="p2",
            record_kind="validated",
        )
        diffs = build_pending_turn_diffs([like_a, like_b], _snapshot())
        assert [like.post_id for like in diffs.likes] == ["p1", "p2"]

    def test_like_post_produces_episodic_memory_diff(self) -> None:
        action = factories.ProposedActionRecordFactory.create(
            run_id=RUN_ID,
            action_type="like_post",
            target_id="p1",
            record_kind="validated",
        )
        diffs = build_pending_turn_diffs([action], _snapshot())
        assert len(diffs.memory_diffs) == 1
        assert diffs.memory_diffs[0].memory_type == "episodic"
        assert diffs.memory_diffs[0].content == "Turn 1: liked post p1"

    def test_no_actions_produces_empty_memory_diffs(self) -> None:
        diffs = build_pending_turn_diffs([], _snapshot())
        assert diffs.memory_diffs == []

    def test_unknown_action_type_raises_value_error(self) -> None:
        action = factories.ProposedActionRecordFactory.create(
            run_id=RUN_ID,
            action_type="unsupported",
            record_kind="validated",
        )
        with pytest.raises(ValueError, match="Unsupported action type"):
            build_pending_turn_diffs([action], _snapshot())
