"""Tests for feeds.feed_generator module."""

from unittest.mock import Mock, patch

import pytest

from db.repositories.generated_feed_repository import GeneratedFeedRepository
from db.repositories.interfaces import (
    RunPostCommentRepository,
    RunPostLikeRepository,
    RunPostRepository,
)
from feeds.algorithms.implementations.chronological import ChronologicalFeedAlgorithm
from feeds.algorithms.interfaces import FeedAlgorithmResult
from feeds.feed_generator import _generate_feed, generate_feeds
from lib.agent_id import canonical_agent_id
from simulation.core.models.feeds import GeneratedFeed
from simulation.core.models.posts import Post, PostSource
from tests.factories import AgentFactory, PostFactory, RunPostSnapshotFactory


@pytest.fixture
def mock_generated_feed_repo():
    """Fixture providing a mock GeneratedFeedRepository."""
    return Mock(spec=GeneratedFeedRepository)


@pytest.fixture
def mock_run_post_repo(sample_posts):
    """Fixture providing a mock RunPostRepository that returns snapshots mapping to sample_posts."""
    mock = Mock(spec=RunPostRepository)
    # Build RunPostSnapshot list that maps to sample_posts for hydration
    snapshots = [
        RunPostSnapshotFactory.create(
            run_post_id=p.post_id,
            run_id="run_123",
            agent_post_id=f"ap_{p.post_id}",
            author_agent_id=canonical_agent_id("author1.bsky.social"),
            author_handle_at_start=p.author_handle,
            author_display_name_at_start=p.author_display_name,
            body_text_at_start=p.text,
            published_at_start=p.created_at,
        )
        for p in sample_posts
    ]
    mock.read_run_posts_by_ids.return_value = snapshots
    return mock


@pytest.fixture
def mock_run_post_like_repo():
    mock = Mock(spec=RunPostLikeRepository)

    def _count_likes(*, run_id, run_post_ids):
        return {pid: 0 for pid in run_post_ids}

    mock.count_likes_by_run_post_ids.side_effect = lambda run_id, run_post_ids: {
        pid: 0 for pid in run_post_ids
    }
    return mock


@pytest.fixture
def mock_run_post_comment_repo():
    mock = Mock(spec=RunPostCommentRepository)
    mock.count_comments_by_run_post_ids.side_effect = lambda run_id, run_post_ids: {
        pid: 0 for pid in run_post_ids
    }
    return mock


@pytest.fixture
def sample_agent():
    """Fixture providing a sample SimulationAgent."""
    return AgentFactory.create(handle="test.bsky.social")


@pytest.fixture
def sample_posts():
    """Fixture providing sample Post objects."""
    return [
        PostFactory.create(
            uri="at://local.test/app.bsky.feed.post/post1",
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
        PostFactory.create(
            uri="at://local.test/app.bsky.feed.post/post2",
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
        PostFactory.create(
            uri="at://local.test/app.bsky.feed.post/post3",
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
    """Tests for _generate_feed function."""

    def test_generates_feed_with_chronological_algorithm(
        self, sample_agent, sample_posts
    ):
        """Test that _generate_feed uses chronological algorithm correctly."""
        # Arrange
        run_id = "run_123"
        turn_number = 0
        feed_algorithm = "chronological"

        # Act
        result = _generate_feed(
            agent=sample_agent,
            candidate_posts=sample_posts,
            run_id=run_id,
            turn_number=turn_number,
            feed_algorithm=feed_algorithm,
            feed_algorithm_config=None,
        )

        # Assert
        assert isinstance(result, GeneratedFeed)
        assert result.run_id == run_id
        assert result.turn_number == turn_number
        assert result.agent_handle == sample_agent.handle
        assert len(result.post_ids) <= 20  # MAX_POSTS_PER_FEED
        # Posts should be sorted by created_at descending (newest first)
        expected_order = [
            "bluesky:at://local.test/app.bsky.feed.post/post3",
            "bluesky:at://local.test/app.bsky.feed.post/post2",
            "bluesky:at://local.test/app.bsky.feed.post/post1",
        ]
        assert result.post_ids == expected_order

    def test_chronological_uses_deterministic_tie_breaking_for_same_created_at(
        self, sample_agent
    ):
        """Test that posts with identical created_at are ordered by uri (ascending)."""
        same_timestamp = "2024-01-02T00:00:00Z"
        posts_same_created_at = [
            PostFactory.create(
                uri="at://local.test/app.bsky.feed.post/post_z",
                author_handle="author.bsky.social",
                author_display_name="Author",
                text="Post Z",
                like_count=0,
                bookmark_count=0,
                quote_count=0,
                reply_count=0,
                repost_count=0,
                created_at=same_timestamp,
            ),
            PostFactory.create(
                uri="at://local.test/app.bsky.feed.post/post_a",
                author_handle="author.bsky.social",
                author_display_name="Author",
                text="Post A",
                like_count=0,
                bookmark_count=0,
                quote_count=0,
                reply_count=0,
                repost_count=0,
                created_at=same_timestamp,
            ),
        ]

        result = _generate_feed(
            agent=sample_agent,
            candidate_posts=posts_same_created_at,
            run_id="run_123",
            turn_number=0,
            feed_algorithm="chronological",
            feed_algorithm_config=None,
        )

        # Uri "a" < "z" alphabetically, so post_a comes before post_z
        expected_order = [
            "bluesky:at://local.test/app.bsky.feed.post/post_a",
            "bluesky:at://local.test/app.bsky.feed.post/post_z",
        ]
        assert result.post_ids == expected_order

    def test_raises_valueerror_for_unknown_algorithm(self, sample_agent, sample_posts):
        """Test that _generate_feed raises ValueError for unknown algorithm."""
        # Arrange
        run_id = "run_123"
        turn_number = 0
        feed_algorithm = "unknown_algorithm"

        # Act & Assert
        with pytest.raises(ValueError, match="feed_algorithm must be one of"):
            _generate_feed(
                agent=sample_agent,
                candidate_posts=sample_posts,
                run_id=run_id,
                turn_number=turn_number,
                feed_algorithm=feed_algorithm,
                feed_algorithm_config=None,
            )

    def test_generate_feed_passes_feed_algorithm_config_to_algorithm(
        self, sample_agent, sample_posts
    ):
        """_generate_feed forwards feed_algorithm_config into algorithm.generate(config=...)."""
        mock_algorithm = Mock()
        mock_algorithm.generate.return_value = FeedAlgorithmResult(
            feed_id="feed-1",
            agent_handle=sample_agent.handle,
            post_ids=[p.uri for p in sample_posts],
        )
        feed_algorithm_config = {"order": "oldest_first"}
        with patch(
            "feeds.feed_generator.get_feed_generator", return_value=mock_algorithm
        ):
            _generate_feed(
                agent=sample_agent,
                candidate_posts=sample_posts,
                run_id="run_123",
                turn_number=0,
                feed_algorithm="chronological",
                feed_algorithm_config=feed_algorithm_config,
            )

        _, kwargs = mock_algorithm.generate.call_args
        expected_result = feed_algorithm_config
        assert kwargs["config"] == expected_result

    def test_chronological_respects_oldest_first_config(
        self, sample_agent, sample_posts
    ):
        """Chronological algorithm supports order=oldest_first."""
        algorithm = ChronologicalFeedAlgorithm()
        result = algorithm.generate(
            candidate_posts=sample_posts,
            agent=sample_agent,
            limit=20,
            config={"order": "oldest_first"},
        )
        expected_result = [
            "bluesky:at://local.test/app.bsky.feed.post/post1",
            "bluesky:at://local.test/app.bsky.feed.post/post2",
            "bluesky:at://local.test/app.bsky.feed.post/post3",
        ]
        assert result.post_ids == expected_result


class TestGenerateFeeds:
    """Tests for generate_feeds function."""

    @patch("feeds.feed_generator.load_candidate_posts")
    def test_generates_feeds_for_multiple_agents(
        self,
        mock_load_candidate_posts,
        mock_generated_feed_repo,
        mock_run_post_repo,
        mock_run_post_like_repo,
        mock_run_post_comment_repo,
        sample_agent,
        sample_posts,
    ):
        """Test that generate_feeds generates feeds for all agents."""
        # Arrange
        agents = [
            AgentFactory.create(handle="agent1.bsky.social"),
            AgentFactory.create(handle="agent2.bsky.social"),
        ]
        run_id = "run_123"
        turn_number = 0
        feed_algorithm = "chronological"

        mock_load_candidate_posts.return_value = sample_posts

        # Act
        result = generate_feeds(
            agents=agents,
            run_id=run_id,
            turn_number=turn_number,
            generated_feed_repo=mock_generated_feed_repo,
            feed_algorithm=feed_algorithm,
            run_post_repo=mock_run_post_repo,
            run_post_like_repo=mock_run_post_like_repo,
            run_post_comment_repo=mock_run_post_comment_repo,
        )

        # Assert
        assert len(result) == 2
        assert "agent1.bsky.social" in result
        assert "agent2.bsky.social" in result
        assert len(result["agent1.bsky.social"]) == len(sample_posts)
        assert len(result["agent2.bsky.social"]) == len(sample_posts)
        # Verify repositories were called
        assert mock_generated_feed_repo.write_generated_feed.call_count == 2
        # Verify run_post_repo was used for hydration
        mock_run_post_repo.read_run_posts_by_ids.assert_called_once()
        call_args = mock_run_post_repo.read_run_posts_by_ids.call_args
        assert call_args.args[0] == run_id
        # Verify load_candidate_posts was called for each agent
        assert mock_load_candidate_posts.call_count == 2

    @patch("feeds.feed_generator.load_candidate_posts")
    def test_uses_batch_queries_for_post_hydration(
        self,
        mock_load_candidate_posts,
        mock_generated_feed_repo,
        mock_run_post_repo,
        mock_run_post_like_repo,
        mock_run_post_comment_repo,
        sample_agent,
        sample_posts,
    ):
        """Test that generate_feeds uses run_post_repo for hydration."""
        # Arrange
        agents = [sample_agent]
        run_id = "run_123"
        turn_number = 0
        feed_algorithm = "chronological"

        mock_load_candidate_posts.return_value = sample_posts

        # Act
        generate_feeds(
            agents=agents,
            run_id=run_id,
            turn_number=turn_number,
            generated_feed_repo=mock_generated_feed_repo,
            feed_algorithm=feed_algorithm,
            run_post_repo=mock_run_post_repo,
            run_post_like_repo=mock_run_post_like_repo,
            run_post_comment_repo=mock_run_post_comment_repo,
        )

        # Assert
        mock_run_post_repo.read_run_posts_by_ids.assert_called_once()
        call_args = mock_run_post_repo.read_run_posts_by_ids.call_args
        assert call_args.args[0] == run_id
        mock_run_post_comment_repo.count_comments_by_run_post_ids.assert_called_once()

    @patch("feeds.feed_generator.load_candidate_posts")
    def test_hydrates_reply_count_from_run_post_comments(
        self,
        mock_load_candidate_posts,
        mock_generated_feed_repo,
        mock_run_post_repo,
        mock_run_post_like_repo,
        mock_run_post_comment_repo,
        sample_agent,
        sample_posts,
    ) -> None:
        mock_load_candidate_posts.return_value = sample_posts
        first_id = sample_posts[0].post_id
        mock_run_post_comment_repo.count_comments_by_run_post_ids.side_effect = (
            lambda run_id, run_post_ids: {
                pid: (2 if pid == first_id else 0) for pid in run_post_ids
            }
        )

        result = generate_feeds(
            agents=[sample_agent],
            run_id="run_123",
            turn_number=0,
            generated_feed_repo=mock_generated_feed_repo,
            feed_algorithm="chronological",
            run_post_repo=mock_run_post_repo,
            run_post_like_repo=mock_run_post_like_repo,
            run_post_comment_repo=mock_run_post_comment_repo,
        )

        hydrated = result[sample_agent.handle]
        by_id = {p.post_id: p for p in hydrated}
        assert by_id[first_id].reply_count == 2
        assert sum(p.reply_count for p in hydrated) == 2

    @patch("feeds.feed_generator.load_candidate_posts")
    @patch("feeds.feed_generator.logger")
    def test_handles_missing_posts_gracefully(
        self,
        mock_logger,
        mock_load_candidate_posts,
        mock_generated_feed_repo,
        mock_run_post_repo,
        mock_run_post_like_repo,
        mock_run_post_comment_repo,
        sample_agent,
        sample_posts,
    ):
        """Test that generate_feeds handles missing posts gracefully."""
        # Arrange
        agents = [sample_agent]
        run_id = "run_123"
        turn_number = 0
        feed_algorithm = "chronological"

        mock_load_candidate_posts.return_value = sample_posts
        # Only return 2 of the 3 posts (missing post3)
        existing_snapshots = [
            RunPostSnapshotFactory.create(
                run_post_id=p.post_id,
                run_id=run_id,
                author_handle_at_start=p.author_handle,
                author_display_name_at_start=p.author_display_name,
                body_text_at_start=p.text,
                published_at_start=p.created_at,
            )
            for p in sample_posts[:2]
        ]
        mock_run_post_repo.read_run_posts_by_ids.return_value = existing_snapshots

        # Act
        result = generate_feeds(
            agents=agents,
            run_id=run_id,
            turn_number=turn_number,
            generated_feed_repo=mock_generated_feed_repo,
            feed_algorithm=feed_algorithm,
            run_post_repo=mock_run_post_repo,
            run_post_like_repo=mock_run_post_like_repo,
            run_post_comment_repo=mock_run_post_comment_repo,
        )

        # Assert
        assert len(result[sample_agent.handle]) == 2
        returned_uris = {post.uri for post in result[sample_agent.handle]}
        expected_uris = {f"seed_state:{p.post_id}" for p in sample_posts[:2]}
        assert returned_uris == expected_uris
        assert mock_logger.warning.called

    @patch("feeds.feed_generator.load_candidate_posts")
    @patch("feeds.feed_generator.logger")
    def test_aggregates_missing_post_warnings(
        self,
        mock_logger,
        mock_load_candidate_posts,
        mock_generated_feed_repo,
        mock_run_post_repo,
        mock_run_post_like_repo,
        mock_run_post_comment_repo,
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
        mock_run_post_repo.read_run_posts_by_ids.return_value = []

        # Act
        result = generate_feeds(
            agents=agents,
            run_id=run_id,
            turn_number=turn_number,
            generated_feed_repo=mock_generated_feed_repo,
            feed_algorithm=feed_algorithm,
            run_post_repo=mock_run_post_repo,
            run_post_like_repo=mock_run_post_like_repo,
            run_post_comment_repo=mock_run_post_comment_repo,
        )

        # Assert
        assert len(result[sample_agent.handle]) == 0
        assert mock_logger.warning.called
        warning_calls = mock_logger.warning.call_args_list
        assert len(warning_calls) > 0
        warning_msg = str(warning_calls[0])
        assert "Missing" in warning_msg or "missing" in warning_msg.lower()

    @patch("feeds.feed_generator.load_candidate_posts")
    def test_writes_feeds_to_database(
        self,
        mock_load_candidate_posts,
        mock_generated_feed_repo,
        mock_run_post_repo,
        mock_run_post_like_repo,
        mock_run_post_comment_repo,
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

        # Act
        generate_feeds(
            agents=agents,
            run_id=run_id,
            turn_number=turn_number,
            generated_feed_repo=mock_generated_feed_repo,
            feed_algorithm=feed_algorithm,
            run_post_repo=mock_run_post_repo,
            run_post_like_repo=mock_run_post_like_repo,
            run_post_comment_repo=mock_run_post_comment_repo,
        )

        # Assert
        # Verify write_generated_feed was called
        mock_generated_feed_repo.write_generated_feed.assert_called_once()
        # Verify the feed passed to the repository has correct values
        call_args = mock_generated_feed_repo.write_generated_feed.call_args[0][0]
        assert isinstance(call_args, GeneratedFeed)
        assert call_args.run_id == run_id
        assert call_args.turn_number == turn_number
        assert call_args.agent_handle == sample_agent.handle

    @patch("feeds.feed_generator.load_candidate_posts")
    def test_returns_hydrated_feeds_dict(
        self,
        mock_load_candidate_posts,
        mock_generated_feed_repo,
        mock_run_post_repo,
        mock_run_post_like_repo,
        mock_run_post_comment_repo,
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

        # Act
        result = generate_feeds(
            agents=agents,
            run_id=run_id,
            turn_number=turn_number,
            generated_feed_repo=mock_generated_feed_repo,
            feed_algorithm=feed_algorithm,
            run_post_repo=mock_run_post_repo,
            run_post_like_repo=mock_run_post_like_repo,
            run_post_comment_repo=mock_run_post_comment_repo,
        )

        # Assert
        assert isinstance(result, dict)
        assert sample_agent.handle in result
        assert isinstance(result[sample_agent.handle], list)
        assert all(isinstance(post, Post) for post in result[sample_agent.handle])
        # Verify posts are hydrated (have full post objects, not just URIs)
        assert len(result[sample_agent.handle]) == len(sample_posts)

    @patch("feeds.feed_generator.load_candidate_posts")
    def test_handles_empty_agent_list(
        self,
        mock_load_candidate_posts,
        mock_generated_feed_repo,
        mock_run_post_repo,
        mock_run_post_like_repo,
        mock_run_post_comment_repo,
    ):
        """Test that generate_feeds handles empty agent list."""
        # Arrange
        agents = []
        run_id = "run_123"
        turn_number = 0
        feed_algorithm = "chronological"
        mock_run_post_repo.read_run_posts_by_ids.return_value = []

        # Act
        result = generate_feeds(
            agents=agents,
            run_id=run_id,
            turn_number=turn_number,
            generated_feed_repo=mock_generated_feed_repo,
            feed_algorithm=feed_algorithm,
            run_post_repo=mock_run_post_repo,
            run_post_like_repo=mock_run_post_like_repo,
            run_post_comment_repo=mock_run_post_comment_repo,
        )

        # Assert
        assert result == {}
        mock_load_candidate_posts.assert_not_called()
        mock_generated_feed_repo.write_generated_feed.assert_not_called()

    @patch("feeds.feed_generator.load_candidate_posts")
    def test_handles_empty_candidate_posts(
        self,
        mock_load_candidate_posts,
        mock_generated_feed_repo,
        mock_run_post_repo,
        mock_run_post_like_repo,
        mock_run_post_comment_repo,
        sample_agent,
    ):
        """Test that generate_feeds handles empty candidate posts."""
        # Arrange
        agents = [sample_agent]
        run_id = "run_123"
        turn_number = 0
        feed_algorithm = "chronological"

        mock_load_candidate_posts.return_value = []
        mock_run_post_repo.read_run_posts_by_ids.return_value = []

        # Act
        result = generate_feeds(
            agents=agents,
            run_id=run_id,
            turn_number=turn_number,
            generated_feed_repo=mock_generated_feed_repo,
            feed_algorithm=feed_algorithm,
            run_post_repo=mock_run_post_repo,
            run_post_like_repo=mock_run_post_like_repo,
            run_post_comment_repo=mock_run_post_comment_repo,
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
        mock_run_post_repo,
        mock_run_post_like_repo,
        mock_run_post_comment_repo,
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

        # Act
        result = generate_feeds(
            agents=agents,
            run_id=run_id,
            turn_number=turn_number,
            generated_feed_repo=mock_generated_feed_repo,
            feed_algorithm=feed_algorithm,
            run_post_repo=mock_run_post_repo,
            run_post_like_repo=mock_run_post_like_repo,
            run_post_comment_repo=mock_run_post_comment_repo,
        )

        # Assert
        # Should succeed with known algorithm
        assert len(result) == 1
        assert sample_agent.handle in result
        # Verify the feed was generated (registry worked)
        mock_generated_feed_repo.write_generated_feed.assert_called_once()

    @patch("feeds.feed_generator.load_candidate_posts")
    def test_hydration_uses_run_posts_when_run_post_repo_provided(
        self,
        mock_load_candidate_posts,
        mock_generated_feed_repo,
        sample_agent,
        mock_run_post_like_repo,
        mock_run_post_comment_repo,
    ):
        """When run_post_repo is provided, hydration uses run_posts not feed_posts."""
        run_id = "run_123"
        turn_number = 0
        feed_algorithm = "chronological"

        run_post_snapshots = [
            RunPostSnapshotFactory.create(
                run_post_id="rp_aaa",
                run_id=run_id,
                author_handle_at_start="author1.bsky.social",
                author_display_name_at_start="Author One",
                body_text_at_start="Post from run_posts",
                published_at_start="2024-01-02T00:00:00Z",
            ),
        ]
        from simulation.core.models.posts import run_post_snapshot_to_post

        run_posts = [run_post_snapshot_to_post(s) for s in run_post_snapshots]
        mock_load_candidate_posts.return_value = run_posts

        mock_run_post_repo = Mock(spec=RunPostRepository)
        mock_run_post_repo.read_run_posts_by_ids.return_value = run_post_snapshots

        result = generate_feeds(
            agents=[sample_agent],
            run_id=run_id,
            turn_number=turn_number,
            generated_feed_repo=mock_generated_feed_repo,
            feed_algorithm=feed_algorithm,
            run_post_repo=mock_run_post_repo,
            run_post_like_repo=mock_run_post_like_repo,
            run_post_comment_repo=mock_run_post_comment_repo,
        )

        mock_run_post_repo.read_run_posts_by_ids.assert_called_once()
        call_args = mock_run_post_repo.read_run_posts_by_ids.call_args
        assert call_args.args[0] == run_id
        assert len(result[sample_agent.handle]) == 1
        hydrated = result[sample_agent.handle][0]
        assert hydrated.source == PostSource.SEED_STATE
        assert hydrated.post_id == "rp_aaa"
        assert hydrated.text == "Post from run_posts"
