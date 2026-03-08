"""Tests for simulation.core.action_generators.like.algorithms.random_simple module."""

from simulation.core.action_generators.like.algorithms import random_simple as mod
from simulation.core.action_generators.like.algorithms.random_simple import (
    TOP_K_POSTS_TO_LIKE,
    RandomSimpleLikeGenerator,
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


class TestRandomSimpleLikeGeneratorGenerate:
    """Tests for RandomSimpleLikeGenerator.generate."""

    def test_returns_empty_when_no_candidates(self):
        """Empty candidates returns empty list."""
        generator = RandomSimpleLikeGenerator()
        result = generator.generate(
            candidates=[],
            run_id="run_1",
            turn_number=0,
            agent_handle="agent1.bsky.social",
        )
        assert result == []

    def test_returns_empty_when_probability_is_zero(self, monkeypatch):
        """Probability gate at 0% yields no likes."""
        monkeypatch.setattr(mod, "LIKE_PROBABILITY", 0.0)
        generator = RandomSimpleLikeGenerator()
        candidates = [_post("post_1", like_count=10), _post("post_2", like_count=5)]
        result = generator.generate(
            candidates=candidates,
            run_id="run_prob0",
            turn_number=0,
            agent_handle="agent1.bsky.social",
        )
        assert result == []

    def test_returns_likes_when_probability_is_100(self, monkeypatch):
        """Probability gate at 100% yields likes for selected candidates."""
        monkeypatch.setattr(mod, "LIKE_PROBABILITY", 1.0)
        generator = RandomSimpleLikeGenerator()
        candidates = [_post("post_1", like_count=10), _post("post_2", like_count=5)]
        result = generator.generate(
            candidates=candidates,
            run_id="run_prob100",
            turn_number=0,
            agent_handle="agent1.bsky.social",
        )
        expected_count = min(TOP_K_POSTS_TO_LIKE, len(candidates))
        assert len(result) == expected_count
        assert all(
            like.like.post_id in ("bluesky:post_1", "bluesky:post_2") for like in result
        )

    def test_respects_top_k_limit(self, monkeypatch):
        """Never returns more than TOP_K likes."""
        monkeypatch.setattr(mod, "LIKE_PROBABILITY", 1.0)
        generator = RandomSimpleLikeGenerator()
        candidates = [_post(f"post_{i}", like_count=i) for i in range(5)]
        result = generator.generate(
            candidates=candidates,
            run_id="run_1",
            turn_number=0,
            agent_handle="agent1.bsky.social",
        )
        assert len(result) <= TOP_K_POSTS_TO_LIKE

    def test_higher_social_proof_preferred(self, monkeypatch):
        """Post with higher like_count is preferred when selecting top-k."""
        monkeypatch.setattr(mod, "LIKE_PROBABILITY", 1.0)
        generator = RandomSimpleLikeGenerator()
        low_social = _post("post_low", like_count=1)
        high_social = _post("post_high", like_count=100)
        candidates = [low_social, high_social]
        result = generator.generate(
            candidates=candidates,
            run_id="run_1",
            turn_number=0,
            agent_handle="agent1.bsky.social",
        )
        post_ids = [like.like.post_id for like in result]
        assert post_ids[0] == "bluesky:post_high"
        assert "bluesky:post_high" in post_ids

    def test_recency_affects_ordering(self, monkeypatch):
        """Newer posts score higher when social proof is equal."""
        monkeypatch.setattr(mod, "LIKE_PROBABILITY", 1.0)
        generator = RandomSimpleLikeGenerator()
        old_post = _post("post_old", created_at="2024_01_01-00:00:00")
        new_post = _post("post_new", created_at="2024_12_31-23:59:59")
        candidates = [old_post, new_post]
        result = generator.generate(
            candidates=candidates,
            run_id="run_1",
            turn_number=0,
            agent_handle="agent1.bsky.social",
        )
        post_ids = [like.like.post_id for like in result]
        assert post_ids[0] == "bluesky:post_new"
        assert "bluesky:post_new" in post_ids

    def test_reproducible_when_random_mocked(self, monkeypatch):
        """With random mocked to fixed values, repeated runs produce same likes."""
        monkeypatch.setattr(mod, "LIKE_PROBABILITY", 1.0)
        fake_random = type("FakeRandom", (), {"random": lambda self: 0.0})()
        monkeypatch.setattr(mod, "random", fake_random)
        generator = RandomSimpleLikeGenerator()
        candidates = [_post("post_a", like_count=3), _post("post_b", like_count=7)]
        run_id = "run_det"
        turn_number = 1
        agent_handle = "agent2.bsky.social"
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
        expected_post_ids = [like.like.post_id for like in result1]
        assert [like.like.post_id for like in result2] == expected_post_ids
        assert len(result1) == len(result2)

    def test_generated_like_has_required_fields(self, monkeypatch):
        """GeneratedLike has valid like_id, agent_id, post_id, explanation, metadata."""
        monkeypatch.setattr(mod, "LIKE_PROBABILITY", 1.0)
        generator = RandomSimpleLikeGenerator()
        candidates = [_post("post_1", like_count=1)]
        result = generator.generate(
            candidates=candidates,
            run_id="run_1",
            turn_number=2,
            agent_handle="agent.bsky.social",
        )
        assert len(result) == 1
        like = result[0]
        assert like.like.like_id == "like_run_1_2_agent.bsky.social_bluesky:post_1"
        assert like.like.agent_id == "agent.bsky.social"
        assert like.like.post_id == "bluesky:post_1"
        assert like.explanation
        assert like.metadata.generation_metadata == {
            "policy": "simple",
            "like_probability": 1.0,
        }
