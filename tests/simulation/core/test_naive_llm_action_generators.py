"""Tests for naive LLM action generators."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from simulation.core.action_generators.comment.algorithms.naive_llm import (
    NaiveLLMCommentGenerator,
)
from simulation.core.action_generators.comment.algorithms.naive_llm.response_models import (
    CommentPrediction,
    CommentPredictionItem,
)
from simulation.core.action_generators.follow.algorithms.naive_llm import (
    NaiveLLMFollowGenerator,
)
from simulation.core.action_generators.follow.algorithms.naive_llm.response_models import (
    FollowPrediction,
)
from simulation.core.action_generators.like.algorithms.naive_llm import (
    NaiveLLMLikeGenerator,
)
from simulation.core.action_generators.like.algorithms.naive_llm.response_models import (
    LikePrediction,
)
from simulation.core.models.posts import Post
from tests.factories import PostFactory


def _post(
    uri: str,
    *,
    author_handle: str | None = None,
    like_count: int = 0,
    repost_count: int = 0,
    reply_count: int = 0,
    created_at: str = "2024_01_01-12:00:00",
) -> Post:
    """Build a Post (Bluesky source) for tests."""
    handle = author_handle if author_handle is not None else f"author-{uri}.bsky.social"
    return PostFactory.create(
        uri=uri,
        author_handle=handle,
        author_display_name=f"Author {uri}",
        text="content",
        like_count=like_count,
        bookmark_count=0,
        quote_count=0,
        reply_count=reply_count,
        repost_count=repost_count,
        created_at=created_at,
    )


@pytest.fixture
def sample_candidates() -> list[Post]:
    """Sample feed posts for testing."""
    return [
        _post("post_1", author_handle="alice.bsky.social", like_count=10),
        _post("post_2", author_handle="bob.bsky.social", like_count=5),
        _post("post_3", author_handle="carol.bsky.social", like_count=3),
    ]


class TestNaiveLLMLikeGenerator:
    """Tests for NaiveLLMLikeGenerator."""

    def test_returns_empty_when_no_candidates(
        self, sample_candidates: list[Post]
    ) -> None:
        """Empty candidates returns empty list."""
        mock_llm = MagicMock()
        generator = NaiveLLMLikeGenerator(llm_service=mock_llm)
        expected_result: list = []

        result = generator.generate(
            candidates=[],
            run_id="run_1",
            turn_number=0,
            agent_handle="agent1.bsky.social",
        )

        assert result == expected_result
        mock_llm.structured_completion.assert_not_called()

    def test_returns_likes_when_mock_returns_valid_ids(
        self,
        sample_candidates: list[Post],
    ) -> None:
        """When mock returns valid post_ids, generator produces GeneratedLikes."""
        mock_llm = MagicMock()
        mock_llm.structured_completion.return_value = LikePrediction(
            post_ids=["bluesky:post_1", "bluesky:post_3"],
        )
        generator = NaiveLLMLikeGenerator(llm_service=mock_llm)

        result = generator.generate(
            candidates=sample_candidates,
            run_id="run_1",
            turn_number=1,
            agent_handle="agent.bsky.social",
        )

        expected_result = [
            ("bluesky:post_1", "agent.bsky.social"),
            ("bluesky:post_3", "agent.bsky.social"),
        ]
        assert [(g.like.post_id, g.like.agent_id) for g in result] == expected_result
        expected_result = "LLM prediction (naive_llm)"
        assert result[0].explanation == expected_result
        mock_llm.structured_completion.assert_called_once()

    def test_filters_invalid_ids(
        self,
        sample_candidates: list[Post],
    ) -> None:
        """LLM returning post_ids not in candidates filters them out."""
        mock_llm = MagicMock()
        mock_llm.structured_completion.return_value = LikePrediction(
            post_ids=["bluesky:post_1", "bluesky:nonexistent", "bluesky:post_2"],
        )
        generator = NaiveLLMLikeGenerator(llm_service=mock_llm)

        result = generator.generate(
            candidates=sample_candidates,
            run_id="run_1",
            turn_number=0,
            agent_handle="agent.bsky.social",
        )

        post_ids = [g.like.post_id for g in result]
        expected_result = ["bluesky:post_1", "bluesky:post_2"]
        assert post_ids == expected_result
        expected_result = "bluesky:nonexistent"
        assert expected_result not in post_ids

    def test_ordering_is_sorted_by_post_id(
        self,
        sample_candidates: list[Post],
    ) -> None:
        """Output is sorted by post_id."""
        mock_llm = MagicMock()
        mock_llm.structured_completion.return_value = LikePrediction(
            post_ids=["bluesky:post_3", "bluesky:post_1"],
        )
        generator = NaiveLLMLikeGenerator(llm_service=mock_llm)

        result = generator.generate(
            candidates=sample_candidates,
            run_id="run_1",
            turn_number=0,
            agent_handle="agent.bsky.social",
        )

        expected_result = ["bluesky:post_1", "bluesky:post_3"]
        assert [g.like.post_id for g in result] == expected_result


class TestNaiveLLMCommentGenerator:
    """Tests for NaiveLLMCommentGenerator."""

    def test_returns_empty_when_no_candidates(
        self, sample_candidates: list[Post]
    ) -> None:
        """Empty candidates returns empty list."""
        mock_llm = MagicMock()
        generator = NaiveLLMCommentGenerator(llm_service=mock_llm)
        expected_result: list = []

        result = generator.generate(
            candidates=[],
            run_id="run_1",
            turn_number=0,
            agent_handle="agent1.bsky.social",
        )

        assert result == expected_result
        mock_llm.structured_completion.assert_not_called()

    def test_returns_comments_when_mock_returns_valid_data(
        self,
        sample_candidates: list[Post],
    ) -> None:
        """When mock returns valid comments, generator produces GeneratedComments."""
        mock_llm = MagicMock()
        mock_llm.structured_completion.return_value = CommentPrediction(
            comments=[
                CommentPredictionItem(post_id="bluesky:post_1", text="Nice post!"),
                CommentPredictionItem(post_id="bluesky:post_2", text="Interesting."),
            ],
        )
        generator = NaiveLLMCommentGenerator(llm_service=mock_llm)

        result = generator.generate(
            candidates=sample_candidates,
            run_id="run_1",
            turn_number=1,
            agent_handle="agent.bsky.social",
        )

        expected_result = [
            ("bluesky:post_1", "Nice post!"),
            ("bluesky:post_2", "Interesting."),
        ]
        assert [(g.comment.post_id, g.comment.text) for g in result] == expected_result
        expected_result = "LLM prediction (naive_llm)"
        assert result[0].explanation == expected_result
        mock_llm.structured_completion.assert_called_once()

    def test_filters_invalid_post_ids(
        self,
        sample_candidates: list[Post],
    ) -> None:
        """LLM returning post_ids not in candidates filters them out."""
        mock_llm = MagicMock()
        mock_llm.structured_completion.return_value = CommentPrediction(
            comments=[
                CommentPredictionItem(post_id="bluesky:post_1", text="Ok"),
                CommentPredictionItem(post_id="bluesky:nonexistent", text="Skipped"),
            ],
        )
        generator = NaiveLLMCommentGenerator(llm_service=mock_llm)

        result = generator.generate(
            candidates=sample_candidates,
            run_id="run_1",
            turn_number=0,
            agent_handle="agent.bsky.social",
        )

        expected_result = 1
        assert len(result) == expected_result
        expected_result = "bluesky:post_1"
        assert result[0].comment.post_id == expected_result
        expected_result = "Ok"
        assert result[0].comment.text == expected_result

    def test_ordering_is_sorted_by_post_id(
        self,
        sample_candidates: list[Post],
    ) -> None:
        """Output is sorted by post_id."""
        mock_llm = MagicMock()
        mock_llm.structured_completion.return_value = CommentPrediction(
            comments=[
                CommentPredictionItem(post_id="bluesky:post_3", text="C"),
                CommentPredictionItem(post_id="bluesky:post_1", text="A"),
            ],
        )
        generator = NaiveLLMCommentGenerator(llm_service=mock_llm)

        result = generator.generate(
            candidates=sample_candidates,
            run_id="run_1",
            turn_number=0,
            agent_handle="agent.bsky.social",
        )

        expected_result = ["bluesky:post_1", "bluesky:post_3"]
        assert [g.comment.post_id for g in result] == expected_result


class TestNaiveLLMFollowGenerator:
    """Tests for NaiveLLMFollowGenerator."""

    def test_returns_empty_when_no_candidates(
        self, sample_candidates: list[Post]
    ) -> None:
        """Empty candidates returns empty list."""
        mock_llm = MagicMock()
        generator = NaiveLLMFollowGenerator(llm_service=mock_llm)
        expected_result: list = []

        result = generator.generate(
            candidates=[],
            run_id="run_1",
            turn_number=0,
            agent_handle="agent1.bsky.social",
        )

        assert result == expected_result
        mock_llm.structured_completion.assert_not_called()

    def test_returns_empty_when_only_self_in_feed(self) -> None:
        """When feed contains only agent's own posts, returns empty."""
        mock_llm = MagicMock()
        generator = NaiveLLMFollowGenerator(llm_service=mock_llm)
        candidates = [_post("p1", author_handle="agent.bsky.social")]

        result = generator.generate(
            candidates=candidates,
            run_id="run_1",
            turn_number=0,
            agent_handle="agent.bsky.social",
        )

        expected_result: list = []
        assert result == expected_result
        mock_llm.structured_completion.assert_not_called()

    def test_returns_follows_when_mock_returns_valid_ids(
        self,
        sample_candidates: list[Post],
    ) -> None:
        """When mock returns valid user_ids, generator produces GeneratedFollows."""
        mock_llm = MagicMock()
        mock_llm.structured_completion.return_value = FollowPrediction(
            user_ids=["alice.bsky.social", "carol.bsky.social"],
        )
        generator = NaiveLLMFollowGenerator(llm_service=mock_llm)

        result = generator.generate(
            candidates=sample_candidates,
            run_id="run_1",
            turn_number=1,
            agent_handle="agent.bsky.social",
        )

        expected_result = ["alice.bsky.social", "carol.bsky.social"]
        assert [g.follow.user_id for g in result] == expected_result
        expected_result = "LLM prediction (naive_llm)"
        assert result[0].explanation == expected_result
        mock_llm.structured_completion.assert_called_once()

    def test_filters_invalid_user_ids(
        self,
        sample_candidates: list[Post],
    ) -> None:
        """LLM returning user_ids not in candidates filters them out."""
        mock_llm = MagicMock()
        mock_llm.structured_completion.return_value = FollowPrediction(
            user_ids=["alice.bsky.social", "unknown.bsky.social"],
        )
        generator = NaiveLLMFollowGenerator(llm_service=mock_llm)

        result = generator.generate(
            candidates=sample_candidates,
            run_id="run_1",
            turn_number=0,
            agent_handle="agent.bsky.social",
        )

        expected_result = 1
        assert len(result) == expected_result
        expected_result = "alice.bsky.social"
        assert result[0].follow.user_id == expected_result

    def test_ordering_is_sorted_by_user_id(
        self,
        sample_candidates: list[Post],
    ) -> None:
        """Output is sorted by user_id."""
        mock_llm = MagicMock()
        mock_llm.structured_completion.return_value = FollowPrediction(
            user_ids=["carol.bsky.social", "alice.bsky.social"],
        )
        generator = NaiveLLMFollowGenerator(llm_service=mock_llm)

        result = generator.generate(
            candidates=sample_candidates,
            run_id="run_1",
            turn_number=0,
            agent_handle="agent.bsky.social",
        )

        expected_result = ["alice.bsky.social", "carol.bsky.social"]
        assert [g.follow.user_id for g in result] == expected_result
