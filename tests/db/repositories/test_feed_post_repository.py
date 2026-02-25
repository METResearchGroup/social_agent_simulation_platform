"""Tests for db.repositories.feed_post_repository module."""

import sqlite3
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from db.adapters.base import FeedPostDatabaseAdapter
from db.repositories.feed_post_repository import SQLiteFeedPostRepository
from simulation.core.models.posts import BlueskyFeedPost
from tests.db.repositories.conftest import make_mock_transaction_provider
from tests.factories import PostFactory


class TestSQLiteFeedPostRepositoryCreateOrUpdateFeedPost:
    """Tests for SQLiteFeedPostRepository.create_or_update_feed_post method."""

    def test_creates_feed_post_with_correct_values(self):
        """Test that create_or_update_feed_post creates a feed post with correct values."""
        # Arrange
        mock_adapter = Mock(spec=FeedPostDatabaseAdapter)
        repo = SQLiteFeedPostRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )
        post = PostFactory.create(
            post_id="at://did:plc:test123/app.bsky.feed.post/test",
            uri="at://did:plc:test123/app.bsky.feed.post/test",
            author_display_name="Test User",
            author_handle="test.bsky.social",
            text="Test post content",
            bookmark_count=5,
            like_count=10,
            quote_count=2,
            reply_count=3,
            repost_count=1,
            created_at="2024-01-01T00:00:00Z",
        )

        # Act
        result = repo.create_or_update_feed_post(post)

        # Assert
        assert result == post
        mock_adapter.write_feed_post.assert_called_once()
        assert mock_adapter.write_feed_post.call_args[0][0] == post
        assert mock_adapter.write_feed_post.call_args[1]["conn"] is not None

    def test_creates_feed_post_with_different_values(self):
        """Test that create_or_update_feed_post handles different post values correctly."""
        # Arrange
        mock_adapter = Mock(spec=FeedPostDatabaseAdapter)
        repo = SQLiteFeedPostRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )
        post = PostFactory.create(
            post_id="at://did:plc:another456/app.bsky.feed.post/another",
            uri="at://did:plc:another456/app.bsky.feed.post/another",
            author_display_name="Another User",
            author_handle="another.bsky.social",
            text="Another post with more content",
            bookmark_count=50,
            like_count=200,
            quote_count=10,
            reply_count=25,
            repost_count=15,
            created_at="2024-02-01T12:00:00Z",
        )

        # Act
        result = repo.create_or_update_feed_post(post)

        # Assert
        assert result.uri == "at://did:plc:another456/app.bsky.feed.post/another"
        assert result.like_count == 200
        assert result.reply_count == 25
        mock_adapter.write_feed_post.assert_called_once()
        assert mock_adapter.write_feed_post.call_args[0][0] == post
        assert mock_adapter.write_feed_post.call_args[1]["conn"] is not None

    def test_persists_feed_post_to_database(self):
        """Test that create_or_update_feed_post persists the post to the database via write_feed_post."""
        # Arrange
        mock_adapter = Mock(spec=FeedPostDatabaseAdapter)
        repo = SQLiteFeedPostRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )
        post = PostFactory.create(
            post_id="at://did:plc:test123/app.bsky.feed.post/test",
            uri="at://did:plc:test123/app.bsky.feed.post/test",
            author_display_name="Test User",
            author_handle="test.bsky.social",
            text="Test post content",
            bookmark_count=5,
            like_count=10,
            quote_count=2,
            reply_count=3,
            repost_count=1,
            created_at="2024-01-01T00:00:00Z",
        )

        # Act
        result = repo.create_or_update_feed_post(post)

        # Assert
        mock_adapter.write_feed_post.assert_called_once()
        call_args = mock_adapter.write_feed_post.call_args[0][0]
        assert isinstance(call_args, BlueskyFeedPost)
        assert mock_adapter.write_feed_post.call_args[1]["conn"] is not None
        assert call_args.uri == result.uri
        assert call_args.text == result.text
        assert call_args.author_handle == result.author_handle

    def test_raises_validation_error_when_uri_is_empty(self):
        """Test that creating BlueskyFeedPost with empty uri raises ValidationError from Pydantic."""
        # Arrange & Act & Assert
        # Pydantic validation happens at model creation time, not in repository
        with pytest.raises(ValidationError) as exc_info:
            PostFactory.create(
                post_id="",
                uri="",
                author_display_name="Test User",
                author_handle="test.bsky.social",
                text="Test post content",
                bookmark_count=5,
                like_count=10,
                quote_count=2,
                reply_count=3,
                repost_count=1,
                created_at="2024-01-01T00:00:00Z",
            )

        assert "uri cannot be empty" in str(exc_info.value)

    def test_raises_validation_error_when_uri_is_whitespace(self):
        """Test that creating BlueskyFeedPost with whitespace uri raises ValidationError from Pydantic."""
        # Arrange & Act & Assert
        # Pydantic validation happens at model creation time, not in repository
        with pytest.raises(ValidationError) as exc_info:
            PostFactory.create(
                post_id="   ",
                uri="   ",
                author_display_name="Test User",
                author_handle="test.bsky.social",
                text="Test post content",
                bookmark_count=5,
                like_count=10,
                quote_count=2,
                reply_count=3,
                repost_count=1,
                created_at="2024-01-01T00:00:00Z",
            )

        assert "uri cannot be empty" in str(exc_info.value)

    def test_propagates_adapter_exception_when_write_fails(self):
        """Test that create_or_update_feed_post propagates adapter exceptions when database write fails."""
        # Arrange
        mock_adapter = Mock(spec=FeedPostDatabaseAdapter)
        db_error = sqlite3.IntegrityError(
            "UNIQUE constraint failed: bluesky_feed_posts.uri"
        )
        mock_adapter.write_feed_post.side_effect = db_error
        repo = SQLiteFeedPostRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )
        post = PostFactory.create(
            post_id="at://did:plc:test123/app.bsky.feed.post/test",
            uri="at://did:plc:test123/app.bsky.feed.post/test",
            author_display_name="Test User",
            author_handle="test.bsky.social",
            text="Test post content",
            bookmark_count=5,
            like_count=10,
            quote_count=2,
            reply_count=3,
            repost_count=1,
            created_at="2024-01-01T00:00:00Z",
        )

        # Act & Assert
        with pytest.raises(sqlite3.IntegrityError) as exc_info:
            repo.create_or_update_feed_post(post)

        assert exc_info.value is db_error
        mock_adapter.write_feed_post.assert_called_once()
        assert mock_adapter.write_feed_post.call_args[0][0] == post
        assert mock_adapter.write_feed_post.call_args[1]["conn"] is not None


class TestSQLiteFeedPostRepositoryCreateOrUpdateFeedPosts:
    """Tests for SQLiteFeedPostRepository.create_or_update_feed_posts method (batch operation)."""

    def test_creates_multiple_feed_posts_with_correct_values(self):
        """Test that create_or_update_feed_posts creates multiple posts with correct values."""
        # Arrange
        mock_adapter = Mock(spec=FeedPostDatabaseAdapter)
        repo = SQLiteFeedPostRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )
        posts = [
            PostFactory.create(
                post_id=f"at://did:plc:test{i}/app.bsky.feed.post/test{i}",
                uri=f"at://did:plc:test{i}/app.bsky.feed.post/test{i}",
                author_display_name=f"User {i}",
                author_handle=f"user{i}.bsky.social",
                text=f"Post {i} content",
                bookmark_count=i,
                like_count=i * 10,
                quote_count=i * 2,
                reply_count=i * 3,
                repost_count=i,
                created_at=f"2024-01-0{i}T00:00:00Z",
            )
            for i in range(1, 4)
        ]

        # Act
        result = repo.create_or_update_feed_posts(posts)

        # Assert
        assert result == posts
        mock_adapter.write_feed_posts.assert_called_once()
        assert mock_adapter.write_feed_posts.call_args[0][0] == posts
        assert mock_adapter.write_feed_posts.call_args[1]["conn"] is not None

    def test_creates_feed_posts_with_empty_list(self):
        """Test that create_or_update_feed_posts handles empty list correctly."""
        # Arrange
        mock_adapter = Mock(spec=FeedPostDatabaseAdapter)
        repo = SQLiteFeedPostRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )
        posts = []

        # Act
        result = repo.create_or_update_feed_posts(posts)

        # Assert
        assert result == []
        mock_adapter.write_feed_posts.assert_called_once()
        assert mock_adapter.write_feed_posts.call_args[0][0] == posts
        assert mock_adapter.write_feed_posts.call_args[1]["conn"] is not None

    def test_raises_value_error_when_posts_is_none(self):
        """Test that create_or_update_feed_posts raises ValueError when posts is None."""
        # Arrange
        mock_adapter = Mock(spec=FeedPostDatabaseAdapter)
        repo = SQLiteFeedPostRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )

        # Act & Assert
        with pytest.raises(ValueError, match="posts cannot be None"):
            repo.create_or_update_feed_posts(None)  # type: ignore

        mock_adapter.write_feed_posts.assert_not_called()

    def test_raises_validation_error_when_any_uri_is_empty(self):
        """Test that creating BlueskyFeedPost with empty uri raises ValidationError from Pydantic."""
        # Arrange & Act & Assert
        # Pydantic validation happens at model creation time, not in repository
        # The post will fail validation when created
        with pytest.raises(ValidationError) as exc_info:
            PostFactory.create(
                post_id="",
                uri="",
                author_display_name="User 2",
                author_handle="user2.bsky.social",
                text="Post 2 content",
                bookmark_count=2,
                like_count=20,
                quote_count=4,
                reply_count=6,
                repost_count=2,
                created_at="2024-01-02T00:00:00Z",
            )

        assert "uri cannot be empty" in str(exc_info.value)

    def test_propagates_adapter_exception_when_batch_write_fails(self):
        """Test that create_or_update_feed_posts propagates adapter exceptions when batch write fails."""
        # Arrange
        mock_adapter = Mock(spec=FeedPostDatabaseAdapter)
        db_error = sqlite3.OperationalError("Database locked")
        mock_adapter.write_feed_posts.side_effect = db_error
        repo = SQLiteFeedPostRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )
        posts = [
            PostFactory.create(
                post_id=f"at://did:plc:test{i}/app.bsky.feed.post/test{i}",
                uri=f"at://did:plc:test{i}/app.bsky.feed.post/test{i}",
                author_display_name=f"User {i}",
                author_handle=f"user{i}.bsky.social",
                text=f"Post {i} content",
                bookmark_count=i,
                like_count=i * 10,
                quote_count=i * 2,
                reply_count=i * 3,
                repost_count=i,
                created_at=f"2024-01-0{i}T00:00:00Z",
            )
            for i in range(1, 3)
        ]

        # Act & Assert
        with pytest.raises(sqlite3.OperationalError) as exc_info:
            repo.create_or_update_feed_posts(posts)

        assert exc_info.value is db_error
        mock_adapter.write_feed_posts.assert_called_once()
        assert mock_adapter.write_feed_posts.call_args[0][0] == posts
        assert mock_adapter.write_feed_posts.call_args[1]["conn"] is not None


class TestSQLiteFeedPostRepositoryGetFeedPost:
    """Tests for SQLiteFeedPostRepository.get_feed_post method."""

    def test_gets_feed_post_when_found(self):
        """Test that get_feed_post returns a post when found."""
        # Arrange
        mock_adapter = Mock(spec=FeedPostDatabaseAdapter)
        expected_post = PostFactory.create(
            post_id="at://did:plc:test123/app.bsky.feed.post/test",
            uri="at://did:plc:test123/app.bsky.feed.post/test",
            author_display_name="Test User",
            author_handle="test.bsky.social",
            text="Test post content",
            bookmark_count=5,
            like_count=10,
            quote_count=2,
            reply_count=3,
            repost_count=1,
            created_at="2024-01-01T00:00:00Z",
        )
        mock_adapter.read_feed_post.return_value = expected_post
        repo = SQLiteFeedPostRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )

        # Act
        result = repo.get_feed_post("at://did:plc:test123/app.bsky.feed.post/test")

        # Assert
        assert result == expected_post
        mock_adapter.read_feed_post.assert_called_once()
        assert mock_adapter.read_feed_post.call_args[0][0] == (
            "at://did:plc:test123/app.bsky.feed.post/test"
        )
        assert mock_adapter.read_feed_post.call_args[1]["conn"] is not None

    def test_raises_value_error_when_feed_post_not_found(self):
        """Test that get_feed_post raises ValueError when post is not found."""
        # Arrange
        mock_adapter = Mock(spec=FeedPostDatabaseAdapter)
        mock_adapter.read_feed_post.side_effect = ValueError(
            "No feed post found for uri: at://did:plc:nonexistent/app.bsky.feed.post/test"
        )
        repo = SQLiteFeedPostRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )

        # Act & Assert
        with pytest.raises(ValueError, match="No feed post found for uri"):
            repo.get_feed_post("at://did:plc:nonexistent/app.bsky.feed.post/test")

        mock_adapter.read_feed_post.assert_called_once()
        assert mock_adapter.read_feed_post.call_args[0][0] == (
            "at://did:plc:nonexistent/app.bsky.feed.post/test"
        )
        assert mock_adapter.read_feed_post.call_args[1]["conn"] is not None

    def test_raises_value_error_when_uri_is_empty(self):
        """Test that get_feed_post raises ValueError when uri is empty."""
        # Arrange
        mock_adapter = Mock(spec=FeedPostDatabaseAdapter)
        repo = SQLiteFeedPostRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )

        # Act & Assert
        with pytest.raises(ValueError, match="uri cannot be empty"):
            repo.get_feed_post("")

        mock_adapter.read_feed_post.assert_not_called()

    def test_raises_value_error_when_uri_is_whitespace(self):
        """Test that get_feed_post raises ValueError when uri is whitespace."""
        # Arrange
        mock_adapter = Mock(spec=FeedPostDatabaseAdapter)
        repo = SQLiteFeedPostRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )

        # Act & Assert
        with pytest.raises(ValueError, match="uri cannot be empty"):
            repo.get_feed_post("   ")

        mock_adapter.read_feed_post.assert_not_called()


class TestSQLiteFeedPostRepositoryListFeedPostsByAuthor:
    """Tests for SQLiteFeedPostRepository.list_feed_posts_by_author method."""

    def test_lists_feed_posts_when_found(self):
        """Test that list_feed_posts_by_author returns posts when found."""
        # Arrange
        mock_adapter = Mock(spec=FeedPostDatabaseAdapter)
        expected_posts = [
            PostFactory.create(
                post_id=f"at://did:plc:test{i}/app.bsky.feed.post/test{i}",
                uri=f"at://did:plc:test{i}/app.bsky.feed.post/test{i}",
                author_display_name="Test User",
                author_handle="test.bsky.social",
                text=f"Post {i} content",
                bookmark_count=i,
                like_count=i * 10,
                quote_count=i * 2,
                reply_count=i * 3,
                repost_count=i,
                created_at=f"2024-01-0{i}T00:00:00Z",
            )
            for i in range(1, 4)
        ]
        mock_adapter.read_feed_posts_by_author.return_value = expected_posts
        repo = SQLiteFeedPostRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )

        # Act
        result = repo.list_feed_posts_by_author("test.bsky.social")

        # Assert
        assert result == expected_posts
        mock_adapter.read_feed_posts_by_author.assert_called_once()
        assert mock_adapter.read_feed_posts_by_author.call_args[0][0] == (
            "test.bsky.social"
        )
        assert mock_adapter.read_feed_posts_by_author.call_args[1]["conn"] is not None

    def test_lists_feed_posts_when_not_found(self):
        """Test that list_feed_posts_by_author returns empty list when no posts found."""
        # Arrange
        mock_adapter = Mock(spec=FeedPostDatabaseAdapter)
        mock_adapter.read_feed_posts_by_author.return_value = []
        repo = SQLiteFeedPostRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )

        # Act
        result = repo.list_feed_posts_by_author("nonexistent.bsky.social")

        # Assert
        assert result == []
        mock_adapter.read_feed_posts_by_author.assert_called_once()
        assert mock_adapter.read_feed_posts_by_author.call_args[0][0] == (
            "nonexistent.bsky.social"
        )
        assert mock_adapter.read_feed_posts_by_author.call_args[1]["conn"] is not None

    def test_raises_value_error_when_author_handle_is_empty(self):
        """Test that list_feed_posts_by_author raises ValueError when author_handle is empty."""
        # Arrange
        mock_adapter = Mock(spec=FeedPostDatabaseAdapter)
        repo = SQLiteFeedPostRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )

        # Act & Assert
        with pytest.raises(ValueError, match="handle cannot be empty"):
            repo.list_feed_posts_by_author("")

        mock_adapter.read_feed_posts_by_author.assert_not_called()

    def test_raises_value_error_when_author_handle_is_whitespace(self):
        """Test that list_feed_posts_by_author raises ValueError when author_handle is whitespace."""
        # Arrange
        mock_adapter = Mock(spec=FeedPostDatabaseAdapter)
        repo = SQLiteFeedPostRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )

        # Act & Assert
        with pytest.raises(ValueError, match="handle cannot be empty"):
            repo.list_feed_posts_by_author("   ")

        mock_adapter.read_feed_posts_by_author.assert_not_called()


class TestSQLiteFeedPostRepositoryListAllFeedPosts:
    """Tests for SQLiteFeedPostRepository.list_all_feed_posts method."""

    def test_lists_all_feed_posts_when_empty(self):
        """Test that list_all_feed_posts returns empty list when no posts exist."""
        # Arrange
        mock_adapter = Mock(spec=FeedPostDatabaseAdapter)
        mock_adapter.read_all_feed_posts.return_value = []
        repo = SQLiteFeedPostRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )

        # Act
        result = repo.list_all_feed_posts()

        # Assert
        assert result == []
        mock_adapter.read_all_feed_posts.assert_called_once()
        assert mock_adapter.read_all_feed_posts.call_args[1]["conn"] is not None

    def test_lists_all_feed_posts_when_posts_exist(self):
        """Test that list_all_feed_posts returns all posts when they exist."""
        # Arrange
        mock_adapter = Mock(spec=FeedPostDatabaseAdapter)
        expected_posts = [
            PostFactory.create(
                post_id=f"at://did:plc:test{i}/app.bsky.feed.post/test{i}",
                uri=f"at://did:plc:test{i}/app.bsky.feed.post/test{i}",
                author_display_name=f"User {i}",
                author_handle=f"user{i}.bsky.social",
                text=f"Post {i} content",
                bookmark_count=i,
                like_count=i * 10,
                quote_count=i * 2,
                reply_count=i * 3,
                repost_count=i,
                created_at=f"2024-01-0{i}T00:00:00Z",
            )
            for i in range(1, 4)
        ]
        mock_adapter.read_all_feed_posts.return_value = expected_posts
        repo = SQLiteFeedPostRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )

        # Act
        result = repo.list_all_feed_posts()

        # Assert
        assert result == expected_posts
        assert len(result) == 3
        mock_adapter.read_all_feed_posts.assert_called_once()
        assert mock_adapter.read_all_feed_posts.call_args[1]["conn"] is not None

    def test_lists_all_feed_posts_returns_correct_order(self):
        """Test that list_all_feed_posts returns posts in the order from adapter."""
        # Arrange
        mock_adapter = Mock(spec=FeedPostDatabaseAdapter)
        expected_posts = [
            PostFactory.create(
                post_id=f"at://did:plc:test{i}/app.bsky.feed.post/test{i}",
                uri=f"at://did:plc:test{i}/app.bsky.feed.post/test{i}",
                author_display_name=f"User {i}",
                author_handle=f"user{i}.bsky.social",
                text=f"Post {i} content",
                bookmark_count=i,
                like_count=i * 10,
                quote_count=i * 2,
                reply_count=i * 3,
                repost_count=i,
                created_at=f"2024-01-0{i}T00:00:00Z",
            )
            for i in range(1, 4)
        ]
        mock_adapter.read_all_feed_posts.return_value = expected_posts
        repo = SQLiteFeedPostRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )

        # Act
        result = repo.list_all_feed_posts()

        # Assert
        assert result[0].uri == "at://did:plc:test1/app.bsky.feed.post/test1"
        assert result[1].uri == "at://did:plc:test2/app.bsky.feed.post/test2"
        assert result[2].uri == "at://did:plc:test3/app.bsky.feed.post/test3"
