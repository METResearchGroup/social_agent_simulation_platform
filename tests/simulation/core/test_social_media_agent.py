"""Tests for simulation.core.models.agents.SocialMediaAgent."""

from unittest.mock import Mock, patch

from simulation.core.models.actions import Follow
from simulation.core.models.agents import SocialMediaAgent
from simulation.core.models.generated.base import GenerationMetadata
from simulation.core.models.generated.follow import GeneratedFollow
from simulation.core.models.posts import BlueskyFeedPost


def _post(post_id: str, *, author_handle: str) -> BlueskyFeedPost:
    """Build a BlueskyFeedPost for tests."""
    return BlueskyFeedPost(
        id=post_id,
        uri=post_id,
        author_handle=author_handle,
        author_display_name=f"Author {post_id}",
        text="content",
        like_count=0,
        bookmark_count=0,
        quote_count=0,
        reply_count=0,
        repost_count=0,
        created_at="2024_01_01-12:00:00",
    )


def test_follow_users_returns_empty_for_empty_feed():
    """follow_users returns [] when feed is empty and does not resolve generator."""
    agent = SocialMediaAgent("agent1.bsky.social")
    with patch("simulation.core.action_generators.get_follow_generator") as mock_get:
        result = agent.follow_users(
            [],
            run_id="run_1",
            turn_number=0,
        )

    expected_result: list = []
    assert result == expected_result
    mock_get.assert_not_called()


def test_follow_users_delegates_to_follow_generator():
    """follow_users delegates candidate generation to configured follow generator."""
    agent = SocialMediaAgent("agent1.bsky.social")
    feed = [_post("post_1", author_handle="author1.bsky.social")]
    generated_follow = GeneratedFollow(
        follow=Follow(
            follow_id="follow_1",
            agent_id=agent.handle,
            user_id="author1.bsky.social",
            created_at="2024_01_01-12:00:00",
        ),
        explanation="reason",
        metadata=GenerationMetadata(created_at="2024_01_01-12:00:00"),
    )
    mock_generator = Mock()
    mock_generator.generate.return_value = [generated_follow]

    with patch(
        "simulation.core.action_generators.get_follow_generator",
        return_value=mock_generator,
    ) as mock_get:
        result = agent.follow_users(
            feed,
            run_id="run_1",
            turn_number=3,
        )

    expected_result = [generated_follow]
    assert result == expected_result
    mock_get.assert_called_once_with()
    mock_generator.generate.assert_called_once_with(
        candidates=feed,
        run_id="run_1",
        turn_number=3,
        agent_handle=agent.handle,
    )
