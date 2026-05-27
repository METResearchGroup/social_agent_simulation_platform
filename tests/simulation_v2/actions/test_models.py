"""Smoke tests for action LLM output models."""

from __future__ import annotations

from simulation_v2.actions.models import (
    LlmCommentOnPostOutput,
    LlmFollowUserOutput,
    LlmGenerationResult,
    LlmLikePostOutput,
    LlmWritePostOutput,
)


class TestActionOutputModels:
    def test_like_post_round_trip(self) -> None:
        model = LlmLikePostOutput(post_ids=["p1", "p2"])
        assert model.model_dump() == {"post_ids": ["p1", "p2"]}
        assert LlmLikePostOutput.model_validate({"post_ids": []}).post_ids == []

    def test_write_post_round_trip(self) -> None:
        model = LlmWritePostOutput(content="hello world")
        assert model.content == "hello world"

    def test_follow_user_round_trip(self) -> None:
        model = LlmFollowUserOutput(user_ids=["u2"])
        assert model.user_ids == ["u2"]

    def test_comment_on_post_round_trip(self) -> None:
        model = LlmCommentOnPostOutput(parent_post_id="p1", content="nice post")
        assert model.parent_post_id == "p1"
        assert model.content == "nice post"

    def test_generation_result_defaults(self) -> None:
        result = LlmGenerationResult(
            status="completed", parsed=LlmWritePostOutput(content="x")
        )
        assert result.error is None
        assert result.latency_ms is None
