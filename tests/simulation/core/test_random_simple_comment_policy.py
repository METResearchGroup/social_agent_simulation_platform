"""Tests for simulation.core.action_generators.comment.algorithms.random_simple module."""

from simulation.core.action_generators.comment.algorithms import random_simple as mod
from simulation.core.action_generators.comment.algorithms.random_simple import (
    TOP_K_POSTS_TO_COMMENT,
    RandomSimpleCommentGenerator,
)
from simulation.core.models.posts import Post
from tests.factories import PostFactory


def _post(
    uri: str,
    *,
    like_count: int = 0,
    repost_count: int = 0,
    reply_count: int = 0,
    created_at: str = "2024_01_01-12:00:00",
) -> Post:
    """Build a Post (Bluesky source) for tests."""
    return PostFactory.create(
        uri=uri,
        author_handle=f"author-{uri}.bsky.social",
        author_display_name=f"Author {uri}",
        text="content",
        like_count=like_count,
        bookmark_count=0,
        quote_count=0,
        reply_count=reply_count,
        repost_count=repost_count,
        created_at=created_at,
    )


class TestRandomSimpleCommentGeneratorGenerate:
    """Tests for RandomSimpleCommentGenerator.generate."""

    def test_returns_empty_when_no_candidates(self):
        """Empty candidates returns empty list."""
        # Arrange
        generator = RandomSimpleCommentGenerator()
        expected_result: list = []

        # Act
        result = generator.generate(
            candidates=[],
            run_id="run_1",
            turn_number=0,
            agent_handle="agent1.bsky.social",
        )

        # Assert
        assert result == expected_result

    def test_returns_empty_when_probability_is_zero(self, monkeypatch):
        """Probability gate at 0% yields no comments."""
        # Arrange
        monkeypatch.setattr(mod, "COMMENT_PROBABILITY", 0.0)
        generator = RandomSimpleCommentGenerator()
        candidates = [_post("post_1", like_count=10), _post("post_2", like_count=5)]
        expected_result: list = []

        # Act
        result = generator.generate(
            candidates=candidates,
            run_id="run_prob0",
            turn_number=0,
            agent_handle="agent1.bsky.social",
        )

        # Assert
        assert result == expected_result

    def test_returns_comments_when_probability_is_100(self, monkeypatch):
        """Probability gate at 100% yields comments for selected candidates."""
        # Arrange
        monkeypatch.setattr(mod, "COMMENT_PROBABILITY", 1.0)
        generator = RandomSimpleCommentGenerator()
        candidates = [_post("post_1", like_count=10), _post("post_2", like_count=5)]
        expected_count = min(TOP_K_POSTS_TO_COMMENT, len(candidates))

        # Act
        result = generator.generate(
            candidates=candidates,
            run_id="run_prob100",
            turn_number=0,
            agent_handle="agent1.bsky.social",
        )

        # Assert
        assert len(result) == expected_count
        assert all(
            c.comment.post_id in ("bluesky:post_1", "bluesky:post_2") for c in result
        )
        assert all(c.comment.text for c in result)

    def test_selection_prefers_higher_social_proof(self, monkeypatch):
        """Top-k selection prefers higher like_count when recency is equal."""
        # Arrange
        monkeypatch.setattr(mod, "COMMENT_PROBABILITY", 1.0)
        generator = RandomSimpleCommentGenerator()
        candidates = [
            _post("post_0", like_count=0),
            _post("post_1", like_count=1),
            _post("post_2", like_count=2),
            _post("post_3", like_count=3),
            _post("post_4", like_count=4),
        ]
        start = max(0, len(candidates) - TOP_K_POSTS_TO_COMMENT)
        expected_selected = {f"bluesky:post_{i}" for i in range(start, len(candidates))}

        # Act
        result = generator.generate(
            candidates=candidates,
            run_id="run_social",
            turn_number=0,
            agent_handle="agent1.bsky.social",
        )

        # Assert
        selected_post_ids = {c.comment.post_id for c in result}
        assert selected_post_ids == expected_selected

    def test_reproducible_when_random_mocked(self, monkeypatch):
        """With random mocked to fixed values, repeated runs produce same comments."""
        # Arrange: probability 1.0 and fixed random so behavior is reproducible
        monkeypatch.setattr(mod, "COMMENT_PROBABILITY", 1.0)
        fake_random = type("FakeRandom", (), {"random": lambda self: 0.0})()
        monkeypatch.setattr(mod, "random", fake_random)
        generator = RandomSimpleCommentGenerator()
        candidates = [_post("post_a", like_count=3), _post("post_b", like_count=7)]
        run_id = "run_det"
        turn_number = 1
        agent_handle = "agent2.bsky.social"

        # Act
        result1 = generator.generate(
            candidates=candidates,
            run_id=run_id,
            turn_number=turn_number,
            agent_handle=agent_handle,
        )
        result2 = generator.generate(
            candidates=candidates,
            run_id=run_id,
            turn_number=turn_number,
            agent_handle=agent_handle,
        )

        # Assert
        expected_post_ids = [c.comment.post_id for c in result1]
        expected_texts = [c.comment.text for c in result1]
        assert [c.comment.post_id for c in result2] == expected_post_ids
        assert [c.comment.text for c in result2] == expected_texts

    def test_ordering_is_sorted_by_post_id(self, monkeypatch):
        """Output ordering is stable and sorted by post_id."""
        # Arrange
        monkeypatch.setattr(mod, "COMMENT_PROBABILITY", 1.0)
        generator = RandomSimpleCommentGenerator()
        candidates = [_post("b"), _post("a")]
        expected_order = ["bluesky:a", "bluesky:b"]

        # Act
        result = generator.generate(
            candidates=candidates,
            run_id="run_order",
            turn_number=0,
            agent_handle="agent1.bsky.social",
        )

        # Assert
        assert [c.comment.post_id for c in result] == expected_order

    def test_generated_comment_has_required_fields(self, monkeypatch):
        """GeneratedComment has valid ids, text, explanation, and metadata."""
        # Arrange
        monkeypatch.setattr(mod, "COMMENT_PROBABILITY", 1.0)
        generator = RandomSimpleCommentGenerator()
        candidates = [_post("post_1", like_count=1)]
        expected_run_id = "run_1"
        expected_turn = 2
        expected_handle = "agent.bsky.social"
        expected_post_id = "bluesky:post_1"
        expected_comment_id = f"comment_{expected_run_id}_{expected_turn}_{expected_handle}_{expected_post_id}"

        # Act
        result = generator.generate(
            candidates=candidates,
            run_id=expected_run_id,
            turn_number=expected_turn,
            agent_handle=expected_handle,
        )

        # Assert
        assert len(result) == 1
        comment = result[0]
        assert comment.comment.comment_id == expected_comment_id
        assert comment.comment.agent_id == expected_handle
        assert comment.comment.post_id == expected_post_id
        assert comment.comment.text
        assert comment.explanation
        assert comment.metadata.generation_metadata == {"policy": "simple"}
