"""Integration tests for db.repositories.generated_feed_repository module.

These tests use a real SQLite database to test end-to-end functionality.
"""

import os
import tempfile

import pytest
from pydantic import ValidationError

from db.adapters.sqlite.sqlite import DB_PATH, get_connection, initialize_database
from db.repositories.generated_feed_repository import (
    create_sqlite_generated_feed_repository,
)
from simulation.core.models.feeds import GeneratedFeed


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    # Save original DB path
    original_path = DB_PATH

    # Create temporary database
    fd, temp_path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)

    # Monkey-patch DB_PATH
    import db.adapters.sqlite.sqlite as sqlite_module

    sqlite_module.DB_PATH = temp_path

    # Initialize the database
    initialize_database()

    yield temp_path

    # Cleanup
    sqlite_module.DB_PATH = original_path
    if os.path.exists(temp_path):
        os.unlink(temp_path)


def _ensure_run_exists(run_id: str) -> None:
    """Ensure a matching `runs` row exists for FK enforcement."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO runs
            (run_id, created_at, total_turns, total_agents, started_at, status, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                "2024-01-01T00:00:00Z",
                1,
                1,
                "2024-01-01T00:00:00Z",
                "running",
                None,
            ),
        )
        conn.commit()


class TestSQLiteGeneratedFeedRepositoryIntegration:
    """Integration tests using a real database."""

    def test_create_and_read_generated_feed(self, temp_db):
        """Test creating a generated feed and reading it back from the database."""
        repo = create_sqlite_generated_feed_repository()
        _ensure_run_exists("run_123")
        feed = GeneratedFeed(
            feed_id="feed_test123",
            run_id="run_123",
            turn_number=1,
            agent_handle="test.bsky.social",
            post_uris=["at://did:plc:test1/app.bsky.feed.post/post1"],
            created_at="2024-01-01T00:00:00Z",
        )

        # Create feed
        created_feed = repo.create_or_update_generated_feed(feed)
        assert created_feed.feed_id == "feed_test123"
        assert created_feed.run_id == "run_123"
        assert created_feed.turn_number == 1

        # Read it back
        retrieved_feed = repo.get_generated_feed("test.bsky.social", "run_123", 1)
        assert retrieved_feed is not None
        assert retrieved_feed.feed_id == created_feed.feed_id
        assert retrieved_feed.run_id == created_feed.run_id
        assert retrieved_feed.turn_number == created_feed.turn_number
        assert retrieved_feed.agent_handle == created_feed.agent_handle
        assert retrieved_feed.post_uris == created_feed.post_uris
        assert retrieved_feed.created_at == created_feed.created_at

    def test_create_or_update_generated_feed_updates_existing_feed(self, temp_db):
        """Test that create_or_update_generated_feed updates an existing feed (composite key)."""
        repo = create_sqlite_generated_feed_repository()
        _ensure_run_exists("run_123")

        # Create initial feed
        initial_feed = GeneratedFeed(
            feed_id="feed_initial",
            run_id="run_123",
            turn_number=1,
            agent_handle="test.bsky.social",
            post_uris=["at://did:plc:test1/app.bsky.feed.post/post1"],
            created_at="2024-01-01T00:00:00Z",
        )
        repo.create_or_update_generated_feed(initial_feed)

        # Update the feed (same composite key, different feed_id and post_uris)
        updated_feed = GeneratedFeed(
            feed_id="feed_updated",
            run_id="run_123",
            turn_number=1,
            agent_handle="test.bsky.social",
            post_uris=[
                "at://did:plc:test1/app.bsky.feed.post/post1",
                "at://did:plc:test2/app.bsky.feed.post/post2",
            ],
            created_at="2024-01-02T00:00:00Z",
        )
        repo.create_or_update_generated_feed(updated_feed)

        # Verify update
        retrieved_feed = repo.get_generated_feed("test.bsky.social", "run_123", 1)
        assert retrieved_feed is not None
        assert retrieved_feed.feed_id == "feed_updated"
        assert retrieved_feed.run_id == "run_123"
        assert retrieved_feed.turn_number == 1
        assert len(retrieved_feed.post_uris) == 2
        assert retrieved_feed.post_uris == [
            "at://did:plc:test1/app.bsky.feed.post/post1",
            "at://did:plc:test2/app.bsky.feed.post/post2",
        ]

    def test_get_generated_feed_raises_value_error_for_nonexistent_composite_key(
        self, temp_db
    ):
        """Test that get_generated_feed raises ValueError for a non-existent composite key."""
        repo = create_sqlite_generated_feed_repository()

        with pytest.raises(ValueError, match="Generated feed not found"):
            repo.get_generated_feed("nonexistent.bsky.social", "run_999", 99)

    def test_list_all_generated_feeds_retrieves_all_feeds(self, temp_db):
        """Test that list_all_generated_feeds retrieves all feeds from the database."""
        repo = create_sqlite_generated_feed_repository()

        # Create multiple feeds
        for i in range(1, 4):
            _ensure_run_exists(f"run_{i}")
        feeds = [
            GeneratedFeed(
                feed_id=f"feed_test{i}",
                run_id=f"run_{i}",
                turn_number=i,
                agent_handle=f"user{i}.bsky.social",
                post_uris=[f"at://did:plc:test{i}/app.bsky.feed.post/post{i}"],
                created_at=f"2024-01-0{i}T00:00:00Z",
            )
            for i in range(1, 4)
        ]

        for feed in feeds:
            repo.create_or_update_generated_feed(feed)

        # List all feeds
        all_feeds = repo.list_all_generated_feeds()

        # Assert
        assert len(all_feeds) == 3
        feed_dict = {(f.agent_handle, f.run_id, f.turn_number): f for f in all_feeds}
        assert ("user1.bsky.social", "run_1", 1) in feed_dict
        assert ("user2.bsky.social", "run_2", 2) in feed_dict
        assert ("user3.bsky.social", "run_3", 3) in feed_dict

        # Verify all fields are correct
        assert feed_dict[("user1.bsky.social", "run_1", 1)].feed_id == "feed_test1"
        assert feed_dict[("user2.bsky.social", "run_2", 2)].post_uris == [
            "at://did:plc:test2/app.bsky.feed.post/post2"
        ]
        assert (
            feed_dict[("user3.bsky.social", "run_3", 3)].created_at
            == "2024-01-03T00:00:00Z"
        )

    def test_list_all_generated_feeds_returns_empty_list_when_no_feeds(self, temp_db):
        """Test that list_all_generated_feeds returns an empty list when no feeds exist."""
        repo = create_sqlite_generated_feed_repository()

        feeds = repo.list_all_generated_feeds()
        assert feeds == []
        assert isinstance(feeds, list)

    def test_multiple_feeds_with_same_agent_handle_but_different_run_id_turn_number(
        self, temp_db
    ):
        """Test that multiple feeds with same agent_handle but different run_id/turn_number can coexist."""
        repo = create_sqlite_generated_feed_repository()
        _ensure_run_exists("run_1")
        _ensure_run_exists("run_2")

        feed1 = GeneratedFeed(
            feed_id="feed_1",
            run_id="run_1",
            turn_number=1,
            agent_handle="alice.bsky.social",
            post_uris=["at://did:plc:test1/app.bsky.feed.post/post1"],
            created_at="2024-01-01T00:00:00Z",
        )
        feed2 = GeneratedFeed(
            feed_id="feed_2",
            run_id="run_1",
            turn_number=2,
            agent_handle="alice.bsky.social",
            post_uris=["at://did:plc:test2/app.bsky.feed.post/post2"],
            created_at="2024-01-02T00:00:00Z",
        )
        feed3 = GeneratedFeed(
            feed_id="feed_3",
            run_id="run_2",
            turn_number=1,
            agent_handle="alice.bsky.social",
            post_uris=["at://did:plc:test3/app.bsky.feed.post/post3"],
            created_at="2024-01-03T00:00:00Z",
        )

        repo.create_or_update_generated_feed(feed1)
        repo.create_or_update_generated_feed(feed2)
        repo.create_or_update_generated_feed(feed3)

        # Retrieve each feed
        retrieved1 = repo.get_generated_feed("alice.bsky.social", "run_1", 1)
        retrieved2 = repo.get_generated_feed("alice.bsky.social", "run_1", 2)
        retrieved3 = repo.get_generated_feed("alice.bsky.social", "run_2", 1)

        assert retrieved1 is not None
        assert retrieved2 is not None
        assert retrieved3 is not None
        assert retrieved1.feed_id == "feed_1"
        assert retrieved2.feed_id == "feed_2"
        assert retrieved3.feed_id == "feed_3"
        assert retrieved1.turn_number == 1
        assert retrieved2.turn_number == 2
        assert retrieved3.turn_number == 1

    def test_create_or_update_generated_feed_with_empty_agent_handle_raises_error(
        self, temp_db
    ):
        """Test that creating GeneratedFeed with empty agent_handle raises ValidationError from Pydantic."""
        # Pydantic validation happens at model creation time, not in repository
        with pytest.raises(ValidationError) as exc_info:
            GeneratedFeed(
                feed_id="feed_test123",
                run_id="run_123",
                turn_number=1,
                agent_handle="",
                post_uris=["at://did:plc:test1/app.bsky.feed.post/post1"],
                created_at="2024-01-01T00:00:00Z",
            )

        assert "agent_handle cannot be empty" in str(exc_info.value)

    def test_get_generated_feed_with_empty_agent_handle_raises_error(self, temp_db):
        """Test that get_generated_feed raises ValueError when agent_handle is empty."""
        repo = create_sqlite_generated_feed_repository()

        with pytest.raises(ValueError, match="agent_handle cannot be empty"):
            repo.get_generated_feed("", "run_123", 1)

    def test_generated_feed_with_multiple_post_uris(self, temp_db):
        """Test that generated feeds with multiple post URIs are handled correctly."""
        repo = create_sqlite_generated_feed_repository()
        _ensure_run_exists("run_123")

        post_uris = [
            f"at://did:plc:test{i}/app.bsky.feed.post/post{i}" for i in range(1, 11)
        ]
        feed = GeneratedFeed(
            feed_id="feed_many_posts",
            run_id="run_123",
            turn_number=1,
            agent_handle="test.bsky.social",
            post_uris=post_uris,
            created_at="2024-01-01T00:00:00Z",
        )

        repo.create_or_update_generated_feed(feed)
        retrieved = repo.get_generated_feed("test.bsky.social", "run_123", 1)

        assert retrieved is not None
        assert retrieved.post_uris == post_uris
        assert len(retrieved.post_uris) == 10

    def test_read_feeds_for_turn_returns_feeds_for_specific_turn(self, temp_db):
        """Test that read_feeds_for_turn returns all feeds for a specific run and turn."""
        repo = create_sqlite_generated_feed_repository()
        _ensure_run_exists("run_123")
        _ensure_run_exists("run_456")

        # Create feeds for different turns
        feed1 = GeneratedFeed(
            feed_id="feed_turn0_agent1",
            run_id="run_123",
            turn_number=0,
            agent_handle="agent1.bsky.social",
            post_uris=["at://did:plc:test1/app.bsky.feed.post/post1"],
            created_at="2024-01-01T00:00:00Z",
        )
        feed2 = GeneratedFeed(
            feed_id="feed_turn0_agent2",
            run_id="run_123",
            turn_number=0,
            agent_handle="agent2.bsky.social",
            post_uris=["at://did:plc:test2/app.bsky.feed.post/post2"],
            created_at="2024-01-01T00:00:01Z",
        )
        feed3 = GeneratedFeed(
            feed_id="feed_turn1_agent1",
            run_id="run_123",
            turn_number=1,
            agent_handle="agent1.bsky.social",
            post_uris=["at://did:plc:test3/app.bsky.feed.post/post3"],
            created_at="2024-01-01T00:00:02Z",
        )
        feed4 = GeneratedFeed(
            feed_id="feed_different_run",
            run_id="run_456",
            turn_number=0,
            agent_handle="agent1.bsky.social",
            post_uris=["at://did:plc:test4/app.bsky.feed.post/post4"],
            created_at="2024-01-01T00:00:03Z",
        )

        repo.create_or_update_generated_feed(feed1)
        repo.create_or_update_generated_feed(feed2)
        repo.create_or_update_generated_feed(feed3)
        repo.create_or_update_generated_feed(feed4)

        # Read feeds for run_123, turn 0
        feeds = repo.read_feeds_for_turn("run_123", 0)

        # Should return only feeds for run_123, turn 0
        assert len(feeds) == 2
        feed_dict = {f.agent_handle: f for f in feeds}
        assert "agent1.bsky.social" in feed_dict
        assert "agent2.bsky.social" in feed_dict
        assert feed_dict["agent1.bsky.social"].feed_id == "feed_turn0_agent1"
        assert feed_dict["agent2.bsky.social"].feed_id == "feed_turn0_agent2"

        # Read feeds for run_123, turn 1
        feeds_turn1 = repo.read_feeds_for_turn("run_123", 1)
        assert len(feeds_turn1) == 1
        assert feeds_turn1[0].feed_id == "feed_turn1_agent1"

    def test_read_feeds_for_turn_returns_empty_list_when_no_feeds(self, temp_db):
        """Test that read_feeds_for_turn returns empty list when no feeds exist for turn."""
        repo = create_sqlite_generated_feed_repository()

        feeds = repo.read_feeds_for_turn("run_999", 99)
        assert feeds == []
        assert isinstance(feeds, list)
