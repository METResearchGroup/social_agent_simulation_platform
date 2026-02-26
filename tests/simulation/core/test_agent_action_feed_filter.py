"""Tests for simulation.core.agent_action_feed_filter module."""

from unittest.mock import Mock

from simulation.core.action_policy import HistoryAwareActionFeedFilter
from tests.factories import PostFactory


def _build_post(post_id: str, author_handle: str):
    return PostFactory.create(
        post_id=post_id,
        uri=post_id,
        author_display_name="Author",
        author_handle=author_handle,
        text=f"text for {post_id}",
        bookmark_count=0,
        like_count=0,
        quote_count=0,
        reply_count=0,
        repost_count=0,
        created_at="2024_01_01-12:00:00",
    )


class TestHistoryAwareActionFeedFilterFilterCandidates:
    """Tests for HistoryAwareActionFeedFilter.filter_candidates."""

    def test_excludes_previously_liked_posts(self):
        """Test that like candidates exclude posts already liked by the agent."""
        # Arrange
        run_id = "run_1"
        agent_handle = "agent.bsky.social"
        post_1 = _build_post("post_1", "author1.bsky.social")
        post_2 = _build_post("post_2", "author2.bsky.social")
        feed = [post_1, post_2]
        action_history_store = Mock()
        action_history_store.has_liked.side_effect = [True, False]
        action_history_store.has_commented.return_value = False
        action_history_store.has_followed.return_value = False
        expected = [post_2]

        # Act
        result = HistoryAwareActionFeedFilter().filter_candidates(
            run_id=run_id,
            agent_handle=agent_handle,
            feed=feed,
            action_history_store=action_history_store,
        )

        # Assert
        assert result.like_candidates == expected

    def test_excludes_previously_commented_posts(self):
        """Test that comment candidates exclude posts already commented by the agent."""
        # Arrange
        run_id = "run_1"
        agent_handle = "agent.bsky.social"
        post_1 = _build_post("post_1", "author1.bsky.social")
        post_2 = _build_post("post_2", "author2.bsky.social")
        feed = [post_1, post_2]
        action_history_store = Mock()
        action_history_store.has_liked.return_value = False
        action_history_store.has_commented.side_effect = [False, True]
        action_history_store.has_followed.return_value = False
        expected = [post_1]

        # Act
        result = HistoryAwareActionFeedFilter().filter_candidates(
            run_id=run_id,
            agent_handle=agent_handle,
            feed=feed,
            action_history_store=action_history_store,
        )

        # Assert
        assert result.comment_candidates == expected

    def test_excludes_previously_followed_authors(self):
        """Test that follow candidates exclude authors already followed by the agent."""
        # Arrange
        run_id = "run_1"
        agent_handle = "agent.bsky.social"
        post_1 = _build_post("post_1", "author1.bsky.social")
        post_2 = _build_post("post_2", "author2.bsky.social")
        feed = [post_1, post_2]
        action_history_store = Mock()
        action_history_store.has_liked.return_value = False
        action_history_store.has_commented.return_value = False
        action_history_store.has_followed.side_effect = [True, False]
        expected = [post_2]

        # Act
        result = HistoryAwareActionFeedFilter().filter_candidates(
            run_id=run_id,
            agent_handle=agent_handle,
            feed=feed,
            action_history_store=action_history_store,
        )

        # Assert
        assert result.follow_candidates == expected

    def test_preserves_all_candidates_when_no_prior_actions(self):
        """Test that all candidates are preserved when history has no prior actions."""
        # Arrange
        run_id = "run_1"
        agent_handle = "agent.bsky.social"
        post_1 = _build_post("post_1", "author1.bsky.social")
        post_2 = _build_post("post_2", "author2.bsky.social")
        feed = [post_1, post_2]
        action_history_store = Mock()
        action_history_store.has_liked.return_value = False
        action_history_store.has_commented.return_value = False
        action_history_store.has_followed.return_value = False
        expected = [post_1, post_2]

        # Act
        result = HistoryAwareActionFeedFilter().filter_candidates(
            run_id=run_id,
            agent_handle=agent_handle,
            feed=feed,
            action_history_store=action_history_store,
        )

        # Assert
        assert result.like_candidates == expected
        assert result.comment_candidates == expected
        assert result.follow_candidates == expected
