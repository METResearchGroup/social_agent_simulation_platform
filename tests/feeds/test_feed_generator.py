"""Tests for feeds.feed_generator module."""

from unittest.mock import Mock, patch

import pytest

from db.repositories.feed_post_repository import FeedPostRepository
from db.repositories.generated_feed_repository import GeneratedFeedRepository
from feeds.feed_generator import generate_feed, generate_feeds
from simulation.core.models.agents import SocialMediaAgent
from simulation.core.models.feeds import GeneratedFeed
from simulation.core.models.posts import BlueskyFeedPost


@pytest.fixture
def mock_generated_feed_repo():
    """Fixture providing a mock GeneratedFeedRepository."""
    return Mock(spec=GeneratedFeedRepository)


@pytest.fixture
def mock_feed_post_repo():
    """Fixture providing a mock FeedPostRepository."""
    return Mock(spec=FeedPostRepository)


@pytest.fixture
def sample_agent():
    """Fixture providing a sample SocialMediaAgent."""
    return SocialMediaAgent(handle="test.bsky.social")


@pytest.fixture
def sample_posts():
    """Fixture providing sample BlueskyFeedPost objects."""
    return [
        BlueskyFeedPost(
            id="at://did:plc:test1/app.bsky.feed.post/post1",
            uri="at://did:plc:test1/app.bsky.feed.post/post1",
            author_handle="author1.bsky.social",
            author_display_name="Author One",
            text="First post",
            like_count=10,
            bookmark_count=2,
            quote_count=1,
            reply_count=3,
            repost_count=0,
            created_at="2024-01-01T00:00:00Z",
        ),
        BlueskyFeedPost(
            id="at://did:plc:test2/app.bsky.feed.post/post2",
            uri="at://did:plc:test2/app.bsky.feed.post/post2",
            author_handle="author2.bsky.social",
            author_display_name="Author Two",
            text="Second post",
            like_count=5,
            bookmark_count=1,
            quote_count=0,
            reply_count=1,
            repost_count=2,
            created_at="2024-01-02T00:00:00Z",
        ),
        BlueskyFeedPost(
            id="at://did:plc:test3/app.bsky.feed.post/post3",
            uri="at://did:plc:test3/app.bsky.feed.post/post3",
            author_handle="author3.bsky.social",
            author_display_name="Author Three",
            text="Third post",
            like_count=15,
            bookmark_count=3,
            quote_count=2,
            reply_count=5,
            repost_count=1,
            created_at="2024-01-03T00:00:00Z",
        ),
    ]


class TestGenerateFeed:
    """Tests for generate_feed function."""

    def test_generates_feed_with_chronological_algorithm(
        self, sample_agent, sample_posts
    ):
        """Test that generate_feed uses chronological algorithm correctly."""
        # Arrange
        run_id = "run_123"
        turn_number = 0
        feed_algorithm = "chronological"

        # Act
        result = generate_feed(
            agent=sample_agent,
            candidate_posts=sample_posts,
            run_id=run_id,
            turn_number=turn_number,
            feed_algorithm=feed_algorithm,
        )

        # Assert
        assert isinstance(result, GeneratedFeed)
        assert result.run_id == run_id
        assert result.turn_number == turn_number
        assert result.agent_handle == sample_agent.handle
        assert len(result.post_uris) <= 20  # MAX_POSTS_PER_FEED
        # Posts should be sorted by created_at descending (newest first)
        assert result.post_uris[0] == "at://did:plc:test3/app.bsky.feed.post/post3"
        assert result.post_uris[1] == "at://did:plc:test2/app.bsky.feed.post/post2"
        assert result.post_uris[2] == "at://did:plc:test1/app.bsky.feed.post/post1"

    def test_raises_valueerror_for_unknown_algorithm(self, sample_agent, sample_posts):
        """Test that generate_feed raises ValueError for unknown algorithm."""
        # Arrange
        run_id = "run_123"
        turn_number = 0
        feed_algorithm = "unknown_algorithm"

        # Act & Assert
        with pytest.raises(
            ValueError, match="Unknown feed algorithm: unknown_algorithm"
        ):
            generate_feed(
                agent=sample_agent,
                candidate_posts=sample_posts,
                run_id=run_id,
                turn_number=turn_number,
                feed_algorithm=feed_algorithm,
            )


class TestGenerateFeeds:
    """Tests for generate_feeds function."""

    @patch("feeds.feed_generator.load_candidate_posts")
    def test_generates_feeds_for_multiple_agents(
        self,
        mock_load_candidate_posts,
        mock_generated_feed_repo,
        mock_feed_post_repo,
        sample_agent,
        sample_posts,
    ):
        """Test that generate_feeds generates feeds for all agents."""
        # Arrange
        agents = [
            SocialMediaAgent(handle="agent1.bsky.social"),
            SocialMediaAgent(handle="agent2.bsky.social"),
        ]
        run_id = "run_123"
        turn_number = 0
        feed_algorithm = "chronological"

        mock_load_candidate_posts.return_value = sample_posts
        mock_feed_post_repo.read_feed_posts_by_uris.return_value = sample_posts

        # Act
        result = generate_feeds(
            agents=agents,
            run_id=run_id,
            turn_number=turn_number,
            generated_feed_repo=mock_generated_feed_repo,
            feed_post_repo=mock_feed_post_repo,
            feed_algorithm=feed_algorithm,
        )

        # Assert
        assert len(result) == 2
        assert "agent1.bsky.social" in result
        assert "agent2.bsky.social" in result
        assert len(result["agent1.bsky.social"]) == len(sample_posts)
        assert len(result["agent2.bsky.social"]) == len(sample_posts)
        # Verify repositories were called
        assert mock_generated_feed_repo.write_generated_feed.call_count == 2
        # Verify batch query was used (not list_all_feed_posts)
        mock_feed_post_repo.read_feed_posts_by_uris.assert_called_once()
        # Verify load_candidate_posts was called for each agent
        assert mock_load_candidate_posts.call_count == 2

    @patch("feeds.feed_generator.load_candidate_posts")
    def test_uses_batch_queries_for_post_hydration(
        self,
        mock_load_candidate_posts,
        mock_generated_feed_repo,
        mock_feed_post_repo,
        sample_agent,
        sample_posts,
    ):
        """Test that generate_feeds uses batch queries instead of loading all posts."""
        # Arrange
        agents = [sample_agent]
        run_id = "run_123"
        turn_number = 0
        feed_algorithm = "chronological"

        mock_load_candidate_posts.return_value = sample_posts
        mock_feed_post_repo.read_feed_posts_by_uris.return_value = sample_posts

        # Act
        generate_feeds(
            agents=agents,
            run_id=run_id,
            turn_number=turn_number,
            generated_feed_repo=mock_generated_feed_repo,
            feed_post_repo=mock_feed_post_repo,
            feed_algorithm=feed_algorithm,
        )

        # Assert
        # Verify batch query was used
        mock_feed_post_repo.read_feed_posts_by_uris.assert_called_once()
        # Verify list_all_feed_posts was NOT called
        mock_feed_post_repo.list_all_feed_posts.assert_not_called()
        # Verify the batch query was called with a set of URIs
        call_args = mock_feed_post_repo.read_feed_posts_by_uris.call_args[0][0]
        assert isinstance(call_args, (set, list, tuple))
        assert len(call_args) == len(sample_posts)

    @patch("feeds.feed_generator.load_candidate_posts")
    @patch("feeds.feed_generator.logger")
    def test_handles_missing_posts_gracefully(
        self,
        mock_logger,
        mock_load_candidate_posts,
        mock_generated_feed_repo,
        mock_feed_post_repo,
        sample_agent,
        sample_posts,
    ):
        """Test that generate_feeds handles missing posts gracefully."""
        # Arrange
        agents = [sample_agent]
        run_id = "run_123"
        turn_number = 0
        feed_algorithm = "chronological"

        # Create a feed with 3 post URIs, but only 2 posts exist in the repository
        mock_load_candidate_posts.return_value = sample_posts
        # Only return 2 of the 3 posts (missing post3)
        existing_posts = sample_posts[:2]
        mock_feed_post_repo.read_feed_posts_by_uris.return_value = existing_posts

        # Act
        result = generate_feeds(
            agents=agents,
            run_id=run_id,
            turn_number=turn_number,
            generated_feed_repo=mock_generated_feed_repo,
            feed_post_repo=mock_feed_post_repo,
            feed_algorithm=feed_algorithm,
        )

        # Assert
        # Should return only the 2 existing posts (chronological algorithm sorts by created_at desc)
        assert len(result[sample_agent.handle]) == 2
        # Verify the returned posts match what was returned from the repository
        # (not necessarily in the same order as sample_posts due to sorting)
        returned_uris = {post.uri for post in result[sample_agent.handle]}
        expected_uris = {post.uri for post in existing_posts}
        assert returned_uris == expected_uris
        # Should log a warning about missing posts
        assert mock_logger.warning.called

    @patch("feeds.feed_generator.load_candidate_posts")
    @patch("feeds.feed_generator.logger")
    def test_aggregates_missing_post_warnings(
        self,
        mock_logger,
        mock_load_candidate_posts,
        mock_generated_feed_repo,
        mock_feed_post_repo,
        sample_agent,
        sample_posts,
    ):
        """Test that missing post warnings are aggregated per agent."""
        # Arrange
        agents = [sample_agent]
        run_id = "run_123"
        turn_number = 0
        feed_algorithm = "chronological"

        mock_load_candidate_posts.return_value = sample_posts
        # Return empty list (all posts missing)
        mock_feed_post_repo.read_feed_posts_by_uris.return_value = []

        # Act
        result = generate_feeds(
            agents=agents,
            run_id=run_id,
            turn_number=turn_number,
            generated_feed_repo=mock_generated_feed_repo,
            feed_post_repo=mock_feed_post_repo,
            feed_algorithm=feed_algorithm,
        )

        # Assert
        # Should return empty list
        assert len(result[sample_agent.handle]) == 0
        # Should log aggregated warning (not per-URI)
        assert mock_logger.warning.called
        # Verify warning message contains aggregated information
        warning_calls = mock_logger.warning.call_args_list
        assert len(warning_calls) > 0
        # Check that the warning message mentions the count of missing posts
        warning_msg = str(warning_calls[0])
        assert "Missing" in warning_msg or "missing" in warning_msg.lower()

    @patch("feeds.feed_generator.load_candidate_posts")
    def test_writes_feeds_to_database(
        self,
        mock_load_candidate_posts,
        mock_generated_feed_repo,
        mock_feed_post_repo,
        sample_agent,
        sample_posts,
    ):
        """Test that generate_feeds writes feeds to the database."""
        # Arrange
        agents = [sample_agent]
        run_id = "run_123"
        turn_number = 0
        feed_algorithm = "chronological"

        mock_load_candidate_posts.return_value = sample_posts
        mock_feed_post_repo.read_feed_posts_by_uris.return_value = sample_posts

        # Act
        generate_feeds(
            agents=agents,
            run_id=run_id,
            turn_number=turn_number,
            generated_feed_repo=mock_generated_feed_repo,
            feed_post_repo=mock_feed_post_repo,
            feed_algorithm=feed_algorithm,
        )

        # Assert
        # Verify write_generated_feed was called
        mock_generated_feed_repo.write_generated_feed.assert_called_once()
        # Verify the feed passed to the repository has correct values
        call_args = mock_generated_feed_repo.write_generated_feed.call_args[
            0
        ][0]
        assert isinstance(call_args, GeneratedFeed)
        assert call_args.run_id == run_id
        assert call_args.turn_number == turn_number
        assert call_args.agent_handle == sample_agent.handle

    @patch("feeds.feed_generator.load_candidate_posts")
    def test_returns_hydrated_feeds_dict(
        self,
        mock_load_candidate_posts,
        mock_generated_feed_repo,
        mock_feed_post_repo,
        sample_agent,
        sample_posts,
    ):
        """Test that generate_feeds returns correctly structured hydrated feeds dict."""
        # Arrange
        agents = [sample_agent]
        run_id = "run_123"
        turn_number = 0
        feed_algorithm = "chronological"

        mock_load_candidate_posts.return_value = sample_posts
        mock_feed_post_repo.read_feed_posts_by_uris.return_value = sample_posts

        # Act
        result = generate_feeds(
            agents=agents,
            run_id=run_id,
            turn_number=turn_number,
            generated_feed_repo=mock_generated_feed_repo,
            feed_post_repo=mock_feed_post_repo,
            feed_algorithm=feed_algorithm,
        )

        # Assert
        assert isinstance(result, dict)
        assert sample_agent.handle in result
        assert isinstance(result[sample_agent.handle], list)
        assert all(
            isinstance(post, BlueskyFeedPost) for post in result[sample_agent.handle]
        )
        # Verify posts are hydrated (have full post objects, not just URIs)
        assert len(result[sample_agent.handle]) == len(sample_posts)

    @patch("feeds.feed_generator.load_candidate_posts")
    def test_handles_empty_agent_list(
        self,
        mock_load_candidate_posts,
        mock_generated_feed_repo,
        mock_feed_post_repo,
    ):
        """Test that generate_feeds handles empty agent list."""
        # Arrange
        agents = []
        run_id = "run_123"
        turn_number = 0
        feed_algorithm = "chronological"
        # Mock should return empty list when called with empty set
        mock_feed_post_repo.read_feed_posts_by_uris.return_value = []

        # Act
        result = generate_feeds(
            agents=agents,
            run_id=run_id,
            turn_number=turn_number,
            generated_feed_repo=mock_generated_feed_repo,
            feed_post_repo=mock_feed_post_repo,
            feed_algorithm=feed_algorithm,
        )

        # Assert
        assert result == {}
        mock_load_candidate_posts.assert_not_called()
        mock_generated_feed_repo.write_generated_feed.assert_not_called()
        # read_feed_posts_by_uris is called with empty set when no agents
        mock_feed_post_repo.read_feed_posts_by_uris.assert_called_once()
        call_args = mock_feed_post_repo.read_feed_posts_by_uris.call_args[0][0]
        assert len(call_args) == 0

    @patch("feeds.feed_generator.load_candidate_posts")
    def test_handles_empty_candidate_posts(
        self,
        mock_load_candidate_posts,
        mock_generated_feed_repo,
        mock_feed_post_repo,
        sample_agent,
    ):
        """Test that generate_feeds handles empty candidate posts."""
        # Arrange
        agents = [sample_agent]
        run_id = "run_123"
        turn_number = 0
        feed_algorithm = "chronological"

        mock_load_candidate_posts.return_value = []
        mock_feed_post_repo.read_feed_posts_by_uris.return_value = []

        # Act
        result = generate_feeds(
            agents=agents,
            run_id=run_id,
            turn_number=turn_number,
            generated_feed_repo=mock_generated_feed_repo,
            feed_post_repo=mock_feed_post_repo,
            feed_algorithm=feed_algorithm,
        )

        # Assert
        assert len(result) == 1
        assert sample_agent.handle in result
        assert result[sample_agent.handle] == []
        # Should still write the feed (even if empty)
        mock_generated_feed_repo.write_generated_feed.assert_called_once()

    @patch("feeds.feed_generator.load_candidate_posts")
    def test_registry_pattern_works_correctly(
        self,
        mock_load_candidate_posts,
        mock_generated_feed_repo,
        mock_feed_post_repo,
        sample_agent,
        sample_posts,
    ):
        """Test that the registry pattern correctly dispatches to algorithms."""
        # Arrange
        agents = [sample_agent]
        run_id = "run_123"
        turn_number = 0
        feed_algorithm = "chronological"

        mock_load_candidate_posts.return_value = sample_posts
        mock_feed_post_repo.read_feed_posts_by_uris.return_value = sample_posts

        # Act
        result = generate_feeds(
            agents=agents,
            run_id=run_id,
            turn_number=turn_number,
            generated_feed_repo=mock_generated_feed_repo,
            feed_post_repo=mock_feed_post_repo,
            feed_algorithm=feed_algorithm,
        )

        # Assert
        # Should succeed with known algorithm
        assert len(result) == 1
        assert sample_agent.handle in result
        # Verify the feed was generated (registry worked)
        mock_generated_feed_repo.write_generated_feed.assert_called_once()
