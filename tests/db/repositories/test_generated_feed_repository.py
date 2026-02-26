"""Tests for db.repositories.generated_feed_repository module."""

from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from db.adapters.base import GeneratedFeedDatabaseAdapter
from db.repositories.generated_feed_repository import SQLiteGeneratedFeedRepository
from simulation.core.models.feeds import GeneratedFeed
from tests.db.repositories.conftest import make_mock_transaction_provider
from tests.factories import GeneratedFeedFactory


class TestSQLiteGeneratedFeedRepositoryCreateOrUpdateGeneratedFeed:
    """Tests for SQLiteGeneratedFeedRepository.write_generated_feed method."""

    def test_creates_generated_feed_with_correct_values(self):
        """Test that write_generated_feed creates a feed with correct values."""
        # Arrange
        mock_adapter = Mock(spec=GeneratedFeedDatabaseAdapter)
        repo = SQLiteGeneratedFeedRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )
        feed = GeneratedFeedFactory.create(
            feed_id="feed_test123",
            run_id="run_123",
            turn_number=1,
            agent_handle="test.bsky.social",
            post_uris=["at://did:plc:test1/app.bsky.feed.post/post1"],
            created_at="2024-01-01T00:00:00Z",
        )

        # Act
        result = repo.write_generated_feed(feed)

        # Assert
        assert result == feed
        mock_adapter.write_generated_feed.assert_called_once()
        assert mock_adapter.write_generated_feed.call_args[0][0] == feed
        assert mock_adapter.write_generated_feed.call_args[1]["conn"] is not None

    def test_creates_generated_feed_with_different_values(self):
        """Test that write_generated_feed handles different feed values correctly."""
        # Arrange
        mock_adapter = Mock(spec=GeneratedFeedDatabaseAdapter)
        repo = SQLiteGeneratedFeedRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )
        feed = GeneratedFeedFactory.create(
            feed_id="feed_another456",
            run_id="run_456",
            turn_number=5,
            agent_handle="another.bsky.social",
            post_uris=[
                "at://did:plc:test1/app.bsky.feed.post/post1",
                "at://did:plc:test2/app.bsky.feed.post/post2",
            ],
            created_at="2024-02-01T12:00:00Z",
        )

        # Act
        result = repo.write_generated_feed(feed)

        # Assert
        assert result.feed_id == "feed_another456"
        assert result.run_id == "run_456"
        assert result.turn_number == 5
        assert len(result.post_uris) == 2
        mock_adapter.write_generated_feed.assert_called_once()
        assert mock_adapter.write_generated_feed.call_args[0][0] == feed
        assert mock_adapter.write_generated_feed.call_args[1]["conn"] is not None

    def test_persists_generated_feed_to_database(self):
        """Test that write_generated_feed persists the feed to the database via write_generated_feed."""
        # Arrange
        mock_adapter = Mock(spec=GeneratedFeedDatabaseAdapter)
        repo = SQLiteGeneratedFeedRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )
        feed = GeneratedFeedFactory.create(
            feed_id="feed_test123",
            run_id="run_123",
            turn_number=1,
            agent_handle="test.bsky.social",
            post_uris=["at://did:plc:test1/app.bsky.feed.post/post1"],
            created_at="2024-01-01T00:00:00Z",
        )

        # Act
        result = repo.write_generated_feed(feed)

        # Assert
        mock_adapter.write_generated_feed.assert_called_once()
        assert mock_adapter.write_generated_feed.call_args[1]["conn"] is not None
        call_args = mock_adapter.write_generated_feed.call_args[0][0]
        assert isinstance(call_args, GeneratedFeed)
        assert call_args.feed_id == result.feed_id
        assert call_args.run_id == result.run_id
        assert call_args.agent_handle == result.agent_handle

    def test_raises_validation_error_when_agent_handle_is_empty(self):
        """Test that creating GeneratedFeed with empty agent_handle raises ValidationError from Pydantic."""
        # Arrange & Act & Assert
        # Pydantic validation happens at model creation time, not in repository
        with pytest.raises(ValidationError) as exc_info:
            GeneratedFeedFactory.create(
                feed_id="feed_test123",
                run_id="run_123",
                turn_number=1,
                agent_handle="",
                post_uris=["at://did:plc:test1/app.bsky.feed.post/post1"],
                created_at="2024-01-01T00:00:00Z",
            )

        assert "agent_handle cannot be empty" in str(exc_info.value)

    def test_raises_validation_error_when_run_id_is_empty(self):
        """Test that creating GeneratedFeed with empty run_id raises ValidationError from Pydantic."""
        # Arrange & Act & Assert
        # Pydantic validation happens at model creation time, not in repository
        with pytest.raises(ValidationError) as exc_info:
            GeneratedFeedFactory.create(
                feed_id="feed_test123",
                run_id="",
                turn_number=1,
                agent_handle="test.bsky.social",
                post_uris=["at://did:plc:test1/app.bsky.feed.post/post1"],
                created_at="2024-01-01T00:00:00Z",
            )

        assert "run_id cannot be empty" in str(exc_info.value)

    def test_propagates_adapter_exception_when_write_fails(self):
        """Test that write_generated_feed propagates adapter exceptions when database write fails."""
        # Arrange
        import sqlite3

        mock_adapter = Mock(spec=GeneratedFeedDatabaseAdapter)
        db_error = sqlite3.IntegrityError(
            "UNIQUE constraint failed: generated_feeds.agent_handle, run_id, turn_number"
        )
        mock_adapter.write_generated_feed.side_effect = db_error
        repo = SQLiteGeneratedFeedRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )
        feed = GeneratedFeedFactory.create(
            feed_id="feed_test123",
            run_id="run_123",
            turn_number=1,
            agent_handle="test.bsky.social",
            post_uris=["at://did:plc:test1/app.bsky.feed.post/post1"],
            created_at="2024-01-01T00:00:00Z",
        )

        # Act & Assert
        with pytest.raises(sqlite3.IntegrityError) as exc_info:
            repo.write_generated_feed(feed)

        assert exc_info.value is db_error
        mock_adapter.write_generated_feed.assert_called_once()
        assert mock_adapter.write_generated_feed.call_args[0][0] == feed
        assert mock_adapter.write_generated_feed.call_args[1]["conn"] is not None


class TestSQLiteGeneratedFeedRepositoryGetGeneratedFeed:
    """Tests for SQLiteGeneratedFeedRepository.get_generated_feed method."""

    def test_gets_generated_feed_when_found(self):
        """Test that get_generated_feed returns a feed when found."""
        # Arrange
        mock_adapter = Mock(spec=GeneratedFeedDatabaseAdapter)
        expected_feed = GeneratedFeedFactory.create(
            feed_id="feed_test123",
            run_id="run_123",
            turn_number=1,
            agent_handle="test.bsky.social",
            post_uris=["at://did:plc:test1/app.bsky.feed.post/post1"],
            created_at="2024-01-01T00:00:00Z",
        )
        mock_adapter.read_generated_feed.return_value = expected_feed
        repo = SQLiteGeneratedFeedRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )

        # Act
        result = repo.get_generated_feed("test.bsky.social", "run_123", 1)

        # Assert
        assert result == expected_feed
        mock_adapter.read_generated_feed.assert_called_once()
        assert mock_adapter.read_generated_feed.call_args[0][:3] == (
            "test.bsky.social",
            "run_123",
            1,
        )
        assert mock_adapter.read_generated_feed.call_args[1]["conn"] is not None

    def test_gets_generated_feed_when_not_found_raises_value_error(self):
        """Test that get_generated_feed raises ValueError when feed is not found (matches current behavior)."""
        # Arrange
        mock_adapter = Mock(spec=GeneratedFeedDatabaseAdapter)
        mock_adapter.read_generated_feed.side_effect = ValueError(
            "Generated feed not found for agent test.bsky.social, run run_123, turn 1"
        )
        repo = SQLiteGeneratedFeedRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Generated feed not found"):
            repo.get_generated_feed("test.bsky.social", "run_123", 1)

        mock_adapter.read_generated_feed.assert_called_once()
        assert mock_adapter.read_generated_feed.call_args[0][:3] == (
            "test.bsky.social",
            "run_123",
            1,
        )
        assert mock_adapter.read_generated_feed.call_args[1]["conn"] is not None

    def test_raises_value_error_when_agent_handle_is_empty(self):
        """Test that get_generated_feed raises ValueError when agent_handle is empty."""
        # Arrange
        mock_adapter = Mock(spec=GeneratedFeedDatabaseAdapter)
        repo = SQLiteGeneratedFeedRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )

        # Act & Assert
        with pytest.raises(ValueError, match="handle cannot be empty"):
            repo.get_generated_feed("", "run_123", 1)

        mock_adapter.read_generated_feed.assert_not_called()

    def test_raises_value_error_when_run_id_is_empty(self):
        """Test that get_generated_feed raises ValueError when run_id is empty."""
        # Arrange
        mock_adapter = Mock(spec=GeneratedFeedDatabaseAdapter)
        repo = SQLiteGeneratedFeedRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )

        # Act & Assert
        with pytest.raises(ValueError, match="run_id cannot be empty"):
            repo.get_generated_feed("test.bsky.social", "", 1)

        mock_adapter.read_generated_feed.assert_not_called()


class TestSQLiteGeneratedFeedRepositoryListAllGeneratedFeeds:
    """Tests for SQLiteGeneratedFeedRepository.list_all_generated_feeds method."""

    def test_lists_all_generated_feeds_when_empty(self):
        """Test that list_all_generated_feeds returns empty list when no feeds exist."""
        # Arrange
        mock_adapter = Mock(spec=GeneratedFeedDatabaseAdapter)
        mock_adapter.read_all_generated_feeds.return_value = []
        repo = SQLiteGeneratedFeedRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )

        # Act
        result = repo.list_all_generated_feeds()

        # Assert
        assert result == []
        mock_adapter.read_all_generated_feeds.assert_called_once()
        assert mock_adapter.read_all_generated_feeds.call_args[1]["conn"] is not None

    def test_lists_all_generated_feeds_when_feeds_exist(self):
        """Test that list_all_generated_feeds returns all feeds when they exist."""
        # Arrange
        mock_adapter = Mock(spec=GeneratedFeedDatabaseAdapter)
        expected_feeds = [
            GeneratedFeedFactory.create(
                feed_id=f"feed_test{i}",
                run_id=f"run_{i}",
                turn_number=i,
                agent_handle=f"user{i}.bsky.social",
                post_uris=[f"at://did:plc:test{i}/app.bsky.feed.post/post{i}"],
                created_at=f"2024-01-0{i}T00:00:00Z",
            )
            for i in range(1, 4)
        ]
        mock_adapter.read_all_generated_feeds.return_value = expected_feeds
        repo = SQLiteGeneratedFeedRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )

        # Act
        result = repo.list_all_generated_feeds()

        # Assert
        assert result == expected_feeds
        assert len(result) == 3
        mock_adapter.read_all_generated_feeds.assert_called_once()
        assert mock_adapter.read_all_generated_feeds.call_args[1]["conn"] is not None

    def test_lists_all_generated_feeds_returns_correct_order(self):
        """Test that list_all_generated_feeds returns feeds in the order from adapter."""
        # Arrange
        mock_adapter = Mock(spec=GeneratedFeedDatabaseAdapter)
        expected_feeds = [
            GeneratedFeedFactory.create(
                feed_id=f"feed_test{i}",
                run_id=f"run_{i}",
                turn_number=i,
                agent_handle=f"user{i}.bsky.social",
                post_uris=[f"at://did:plc:test{i}/app.bsky.feed.post/post{i}"],
                created_at=f"2024-01-0{i}T00:00:00Z",
            )
            for i in range(1, 4)
        ]
        mock_adapter.read_all_generated_feeds.return_value = expected_feeds
        repo = SQLiteGeneratedFeedRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )

        # Act
        result = repo.list_all_generated_feeds()

        # Assert
        assert result[0].feed_id == "feed_test1"
        assert result[1].feed_id == "feed_test2"
        assert result[2].feed_id == "feed_test3"


class TestSQLiteGeneratedFeedRepositoryReadFeedsForTurn:
    """Tests for SQLiteGeneratedFeedRepository.read_feeds_for_turn method."""

    def test_reads_feeds_for_turn_when_found(self):
        """Test that read_feeds_for_turn returns feeds when found."""
        # Arrange
        mock_adapter = Mock(spec=GeneratedFeedDatabaseAdapter)
        expected_feeds = [
            GeneratedFeedFactory.create(
                feed_id="feed_test123",
                run_id="run_123",
                turn_number=0,
                agent_handle="test.bsky.social",
                post_uris=["at://did:plc:test1/app.bsky.feed.post/post1"],
                created_at="2024-01-01T00:00:00Z",
            )
        ]
        mock_adapter.read_feeds_for_turn.return_value = expected_feeds
        repo = SQLiteGeneratedFeedRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )

        # Act
        result = repo.read_feeds_for_turn("run_123", 0)

        # Assert
        assert result == expected_feeds
        mock_adapter.read_feeds_for_turn.assert_called_once()
        assert mock_adapter.read_feeds_for_turn.call_args[0][:2] == ("run_123", 0)
        assert mock_adapter.read_feeds_for_turn.call_args[1]["conn"] is not None

    def test_reads_feeds_for_turn_returns_empty_list_when_no_feeds(self):
        """Test that read_feeds_for_turn returns empty list when no feeds found."""
        # Arrange
        mock_adapter = Mock(spec=GeneratedFeedDatabaseAdapter)
        mock_adapter.read_feeds_for_turn.return_value = []
        repo = SQLiteGeneratedFeedRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )

        # Act
        result = repo.read_feeds_for_turn("run_123", 0)

        # Assert
        assert result == []
        mock_adapter.read_feeds_for_turn.assert_called_once()
        assert mock_adapter.read_feeds_for_turn.call_args[0][:2] == ("run_123", 0)
        assert mock_adapter.read_feeds_for_turn.call_args[1]["conn"] is not None

    def test_raises_value_error_when_run_id_is_empty(self):
        """Test that read_feeds_for_turn raises ValueError when run_id is empty."""
        # Arrange
        mock_adapter = Mock(spec=GeneratedFeedDatabaseAdapter)
        repo = SQLiteGeneratedFeedRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )

        # Act & Assert
        with pytest.raises(ValueError, match="run_id cannot be empty"):
            repo.read_feeds_for_turn("", 0)

        mock_adapter.read_feeds_for_turn.assert_not_called()

    def test_raises_value_error_when_run_id_is_whitespace_only(self):
        """Test that read_feeds_for_turn raises ValueError when run_id is whitespace only."""
        # Arrange
        mock_adapter = Mock(spec=GeneratedFeedDatabaseAdapter)
        repo = SQLiteGeneratedFeedRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )

        # Act & Assert
        with pytest.raises(ValueError, match="run_id cannot be empty"):
            repo.read_feeds_for_turn("   ", 0)

        mock_adapter.read_feeds_for_turn.assert_not_called()

    def test_raises_value_error_when_turn_number_is_negative(self):
        """Test that read_feeds_for_turn raises ValueError when turn_number is negative."""
        # Arrange
        mock_adapter = Mock(spec=GeneratedFeedDatabaseAdapter)
        repo = SQLiteGeneratedFeedRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )

        # Act & Assert
        with pytest.raises(ValueError, match="turn_number must be >= 0"):
            repo.read_feeds_for_turn("run_123", -1)

        mock_adapter.read_feeds_for_turn.assert_not_called()

    def test_propagates_adapter_exception_when_read_fails(self):
        """Test that read_feeds_for_turn propagates adapter exceptions when database read fails."""
        # Arrange
        import sqlite3

        mock_adapter = Mock(spec=GeneratedFeedDatabaseAdapter)
        db_error = sqlite3.OperationalError("Database connection failed")
        mock_adapter.read_feeds_for_turn.side_effect = db_error
        repo = SQLiteGeneratedFeedRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )

        # Act & Assert
        with pytest.raises(sqlite3.OperationalError) as exc_info:
            repo.read_feeds_for_turn("run_123", 0)

        assert exc_info.value is db_error
        mock_adapter.read_feeds_for_turn.assert_called_once()
        assert mock_adapter.read_feeds_for_turn.call_args[0][:2] == ("run_123", 0)
        assert mock_adapter.read_feeds_for_turn.call_args[1]["conn"] is not None


class TestSQLiteGeneratedFeedRepositoryEdgeCases:
    """Additional edge case tests for SQLiteGeneratedFeedRepository."""

    def test_write_generated_feed_with_empty_post_uris_list(self):
        """Test that write_generated_feed handles empty post_uris list."""
        # Arrange
        mock_adapter = Mock(spec=GeneratedFeedDatabaseAdapter)
        repo = SQLiteGeneratedFeedRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )
        feed = GeneratedFeedFactory.create(
            feed_id="feed_empty",
            run_id="run_123",
            turn_number=0,
            agent_handle="test.bsky.social",
            post_uris=[],  # Empty list
            created_at="2024-01-01T00:00:00Z",
        )

        # Act
        result = repo.write_generated_feed(feed)

        # Assert
        assert result == feed
        assert result.post_uris == []
        mock_adapter.write_generated_feed.assert_called_once()

    def test_write_generated_feed_with_large_post_uris_list(self):
        """Test that write_generated_feed handles large post_uris list."""
        # Arrange
        mock_adapter = Mock(spec=GeneratedFeedDatabaseAdapter)
        repo = SQLiteGeneratedFeedRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )
        large_uris = [f"at://did:plc:test{i}/app.bsky.feed.post/post{i}" for i in range(1000)]
        feed = GeneratedFeedFactory.create(
            feed_id="feed_large",
            run_id="run_123",
            turn_number=0,
            agent_handle="test.bsky.social",
            post_uris=large_uris,
            created_at="2024-01-01T00:00:00Z",
        )

        # Act
        result = repo.write_generated_feed(feed)

        # Assert
        assert result == feed
        assert len(result.post_uris) == 1000
        mock_adapter.write_generated_feed.assert_called_once()

    def test_write_generated_feed_with_maximum_turn_number(self):
        """Test that write_generated_feed handles maximum turn number."""
        # Arrange
        mock_adapter = Mock(spec=GeneratedFeedDatabaseAdapter)
        repo = SQLiteGeneratedFeedRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )
        feed = GeneratedFeedFactory.create(
            feed_id="feed_max_turn",
            run_id="run_123",
            turn_number=999999,
            agent_handle="test.bsky.social",
            post_uris=["at://did:plc:test1/app.bsky.feed.post/post1"],
            created_at="2024-01-01T00:00:00Z",
        )

        # Act
        result = repo.write_generated_feed(feed)

        # Assert
        assert result == feed
        assert result.turn_number == 999999
        mock_adapter.write_generated_feed.assert_called_once()

    def test_get_post_uris_for_run_returns_empty_set_when_no_feeds(self):
        """Test that get_post_uris_for_run returns empty set when no feeds exist."""
        # Arrange
        mock_adapter = Mock(spec=GeneratedFeedDatabaseAdapter)
        mock_adapter.read_post_uris_for_run.return_value = set()
        repo = SQLiteGeneratedFeedRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )

        # Act
        result = repo.get_post_uris_for_run("test.bsky.social", "run_123")

        # Assert
        assert result == set()
        assert isinstance(result, set)
        mock_adapter.read_post_uris_for_run.assert_called_once()

    def test_get_post_uris_for_run_handles_large_result_set(self):
        """Test that get_post_uris_for_run handles large set of URIs."""
        # Arrange
        mock_adapter = Mock(spec=GeneratedFeedDatabaseAdapter)
        large_uris = {f"at://did:plc:test{i}/app.bsky.feed.post/post{i}" for i in range(5000)}
        mock_adapter.read_post_uris_for_run.return_value = large_uris
        repo = SQLiteGeneratedFeedRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )

        # Act
        result = repo.get_post_uris_for_run("test.bsky.social", "run_123")

        # Assert
        assert result == large_uris
        assert len(result) == 5000
        mock_adapter.read_post_uris_for_run.assert_called_once()

    def test_get_post_uris_for_run_raises_error_when_agent_handle_empty(self):
        """Test that get_post_uris_for_run raises ValueError when agent_handle is empty."""
        # Arrange
        mock_adapter = Mock(spec=GeneratedFeedDatabaseAdapter)
        repo = SQLiteGeneratedFeedRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )

        # Act & Assert
        with pytest.raises(ValueError, match="handle cannot be empty"):
            repo.get_post_uris_for_run("", "run_123")

        mock_adapter.read_post_uris_for_run.assert_not_called()

    def test_get_post_uris_for_run_raises_error_when_run_id_empty(self):
        """Test that get_post_uris_for_run raises ValueError when run_id is empty."""
        # Arrange
        mock_adapter = Mock(spec=GeneratedFeedDatabaseAdapter)
        repo = SQLiteGeneratedFeedRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )

        # Act & Assert
        with pytest.raises(ValueError, match="run_id cannot be empty"):
            repo.get_post_uris_for_run("test.bsky.social", "")

        mock_adapter.read_post_uris_for_run.assert_not_called()