"""Tests for simulation.core.models.agents.SocialMediaAgent."""

from unittest.mock import Mock, patch

from tests.factories import (
    AgentFactory,
    FollowFactory,
    GeneratedFollowFactory,
    GenerationMetadataFactory,
    PostFactory,
)


def test_follow_users_returns_empty_for_empty_feed():
    """follow_users returns [] when feed is empty and does not resolve generator."""
    agent = AgentFactory.create(handle="agent1.bsky.social")
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
    agent = AgentFactory.create(handle="agent1.bsky.social")
    feed = [
        PostFactory.create(
            uri="post_1",
            author_handle="author1.bsky.social",
            author_display_name="Author post_1",
            text="content",
            like_count=0,
            bookmark_count=0,
            quote_count=0,
            reply_count=0,
            repost_count=0,
            created_at="2024_01_01-12:00:00",
        )
    ]
    generated_follow = GeneratedFollowFactory.create(
        follow=FollowFactory.create(
            follow_id="follow_1",
            agent_id=agent.handle,
            user_id="author1.bsky.social",
            created_at="2024_01_01-12:00:00",
        ),
        explanation="reason",
        metadata=GenerationMetadataFactory.create(created_at="2024_01_01-12:00:00"),
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
