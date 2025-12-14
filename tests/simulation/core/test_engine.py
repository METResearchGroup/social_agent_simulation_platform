"""Tests for simulation.core.engine module."""

import logging
from unittest.mock import Mock, patch

import pytest

from db.exceptions import RunNotFoundError
from db.repositories.feed_post_repository import FeedPostRepository
from db.repositories.generated_bio_repository import GeneratedBioRepository
from db.repositories.generated_feed_repository import GeneratedFeedRepository
from db.repositories.profile_repository import ProfileRepository
from db.repositories.run_repository import RunRepository
from simulation.core.engine import SimulationEngine
from simulation.core.models.feeds import GeneratedFeed
from simulation.core.models.posts import BlueskyFeedPost
from simulation.core.models.runs import Run, RunStatus
from simulation.core.models.turns import TurnData


@pytest.fixture
def mock_repos():
    """Fixture that creates and returns a dictionary of mock repositories."""
    return {
        "run_repo": Mock(spec=RunRepository),
        "profile_repo": Mock(spec=ProfileRepository),
        "feed_post_repo": Mock(spec=FeedPostRepository),
        "generated_bio_repo": Mock(spec=GeneratedBioRepository),
        "generated_feed_repo": Mock(spec=GeneratedFeedRepository),
    }


@pytest.fixture
def engine(mock_repos):
    """Fixture that creates and returns a SimulationEngine with mock repositories."""
    return SimulationEngine(
        run_repo=mock_repos["run_repo"],
        profile_repo=mock_repos["profile_repo"],
        feed_post_repo=mock_repos["feed_post_repo"],
        generated_bio_repo=mock_repos["generated_bio_repo"],
        generated_feed_repo=mock_repos["generated_feed_repo"],
    )


@pytest.fixture
def sample_run():
    """Fixture providing a standard Run object for tests."""
    return Run(
        run_id="run_123",
        created_at="2024_01_01-12:00:00",
        total_turns=10,
        total_agents=5,
        started_at="2024_01_01-12:00:00",
        status=RunStatus.RUNNING,
        completed_at=None,
    )


@pytest.fixture
def sample_feed1(sample_run):
    """Fixture providing a standard GeneratedFeed for agent1."""
    return GeneratedFeed(
        feed_id="feed_1",
        run_id=sample_run.run_id,
        turn_number=0,
        agent_handle="agent1.bsky.social",
        post_uris=["uri1", "uri2"],
        created_at="2024_01_01-12:00:00",
    )


@pytest.fixture
def sample_feed2(sample_run):
    """Fixture providing a standard GeneratedFeed for agent2."""
    return GeneratedFeed(
        feed_id="feed_2",
        run_id=sample_run.run_id,
        turn_number=0,
        agent_handle="agent2.bsky.social",
        post_uris=["uri3"],
        created_at="2024_01_01-12:00:01",
    )


@pytest.fixture
def sample_posts():
    """Fixture providing standard BlueskyFeedPost objects for tests."""
    return [
        BlueskyFeedPost(
            id="uri1",
            uri="uri1",
            author_display_name="Author 1",
            author_handle="author1.bsky.social",
            text="Post 1 text",
            bookmark_count=0,
            like_count=5,
            quote_count=0,
            reply_count=2,
            repost_count=1,
            created_at="2024_01_01-12:00:00",
        ),
        BlueskyFeedPost(
            id="uri2",
            uri="uri2",
            author_display_name="Author 2",
            author_handle="author2.bsky.social",
            text="Post 2 text",
            bookmark_count=1,
            like_count=10,
            quote_count=0,
            reply_count=3,
            repost_count=2,
            created_at="2024_01_01-12:01:00",
        ),
        BlueskyFeedPost(
            id="uri3",
            uri="uri3",
            author_display_name="Author 3",
            author_handle="author3.bsky.social",
            text="Post 3 text",
            bookmark_count=0,
            like_count=0,
            quote_count=0,
            reply_count=0,
            repost_count=0,
            created_at="2024_01_01-12:02:00",
        ),
    ]


@pytest.fixture
def default_test_params():
    """Fixture providing default test parameters."""
    return {
        "run_id": "run_123",
        "turn_number": 0,
    }


class TestSimulationEngineGetRun:
    """Tests for SimulationEngine.get_run method."""

    def test_returns_run_when_found(self, engine, mock_repos):
        """Test that get_run returns a Run when it exists."""
        # Arrange
        run_id = "run_123"
        expected_run = Run(
            run_id=run_id,
            created_at="2024_01_01-12:00:00",
            total_turns=10,
            total_agents=5,
            started_at="2024_01_01-12:00:00",
            status=RunStatus.RUNNING,
            completed_at=None,
        )
        mock_repos["run_repo"].get_run.return_value = expected_run

        # Act
        result = engine.get_run(run_id)

        # Assert
        assert result is not None
        assert result == expected_run
        mock_repos["run_repo"].get_run.assert_called_once_with(run_id)

    def test_returns_none_when_run_not_found(self, engine, mock_repos):
        """Test that get_run returns None when run does not exist."""
        # Arrange
        run_id = "nonexistent_run"
        mock_repos["run_repo"].get_run.return_value = None

        # Act
        result = engine.get_run(run_id)

        # Assert
        assert result is None
        mock_repos["run_repo"].get_run.assert_called_once_with(run_id)

    def test_raises_value_error_for_empty_run_id(self, engine, mock_repos):
        """Test that get_run raises ValueError for empty run_id."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="run_id cannot be empty"):
            engine.get_run("")

        # Verify repository was not called
        mock_repos["run_repo"].get_run.assert_not_called()

    def test_raises_value_error_for_whitespace_only_run_id(self, engine, mock_repos):
        """Test that get_run raises ValueError for whitespace-only run_id."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="run_id cannot be empty"):
            engine.get_run("   ")

        # Verify repository was not called
        mock_repos["run_repo"].get_run.assert_not_called()

    def test_raises_value_error_for_none_run_id(self, engine, mock_repos):
        """Test that get_run raises ValueError for None run_id."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="run_id cannot be empty"):
            engine.get_run(None)  # type: ignore

        # Verify repository was not called
        mock_repos["run_repo"].get_run.assert_not_called()

    def test_repository_exceptions_propagate(self, engine, mock_repos):
        """Test that repository exceptions propagate without wrapping."""
        # Arrange
        run_id = "run_123"
        original_error = RunNotFoundError(run_id)
        mock_repos["run_repo"].get_run.side_effect = original_error

        # Act & Assert
        with pytest.raises(RunNotFoundError) as exc_info:
            engine.get_run(run_id)

        # Verify it's the same exception (not wrapped)
        assert exc_info.value is original_error
        mock_repos["run_repo"].get_run.assert_called_once_with(run_id)


class TestSimulationEngineListRuns:
    """Tests for SimulationEngine.list_runs method."""

    def test_returns_list_of_runs(self, engine, mock_repos):
        """Test that list_runs returns a list of runs."""
        # Arrange
        expected_runs = [
            Run(
                run_id="run_1",
                created_at="2024_01_01-12:00:00",
                total_turns=10,
                total_agents=5,
                started_at="2024_01_01-12:00:00",
                status=RunStatus.RUNNING,
                completed_at=None,
            ),
            Run(
                run_id="run_2",
                created_at="2024_01_02-12:00:00",
                total_turns=20,
                total_agents=10,
                started_at="2024_01_02-12:00:00",
                status=RunStatus.COMPLETED,
                completed_at="2024_01_02-13:00:00",
            ),
        ]
        mock_repos["run_repo"].list_runs.return_value = expected_runs

        # Act
        result = engine.list_runs()

        # Assert
        assert result == expected_runs
        assert len(result) == 2
        mock_repos["run_repo"].list_runs.assert_called_once()

    def test_returns_empty_list_when_no_runs_exist(self, engine, mock_repos):
        """Test that list_runs returns empty list when no runs exist."""
        # Arrange
        mock_repos["run_repo"].list_runs.return_value = []

        # Act
        result = engine.list_runs()

        # Assert
        assert result == []
        assert len(result) == 0
        mock_repos["run_repo"].list_runs.assert_called_once()

    def test_repository_exceptions_propagate(self, engine, mock_repos):
        """Test that repository exceptions propagate without wrapping."""
        # Arrange
        original_error = RuntimeError("Database connection failed")
        mock_repos["run_repo"].list_runs.side_effect = original_error

        # Act & Assert
        with pytest.raises(RuntimeError) as exc_info:
            engine.list_runs()

        # Verify it's the same exception (not wrapped)
        assert exc_info.value is original_error
        mock_repos["run_repo"].list_runs.assert_called_once()


class TestSimulationEngineGetTurnData:
    """Tests for SimulationEngine.get_turn_data method."""

    def test_returns_turn_data_with_feeds_and_posts(
        self,
        engine,
        mock_repos,
        sample_run,
        sample_feed1,
        sample_feed2,
        sample_posts,
        default_test_params,
    ):
        """Test that get_turn_data returns TurnData with correct feeds and posts."""
        # Arrange
        run_id = default_test_params["run_id"]
        turn_number = default_test_params["turn_number"]

        mock_repos["run_repo"].get_run.return_value = sample_run
        mock_repos["generated_feed_repo"].read_feeds_for_turn.return_value = [
            sample_feed1,
            sample_feed2,
        ]
        mock_repos["feed_post_repo"].read_feed_posts_by_uris.return_value = sample_posts

        # Act
        result = engine.get_turn_data(run_id, turn_number)

        # Assert
        assert result is not None
        assert isinstance(result, TurnData)
        assert result.turn_number == turn_number
        assert result.agents == []
        assert result.actions == {}
        assert len(result.feeds) == 2
        assert "agent1.bsky.social" in result.feeds
        assert "agent2.bsky.social" in result.feeds
        assert len(result.feeds["agent1.bsky.social"]) == 2
        assert len(result.feeds["agent2.bsky.social"]) == 1
        assert result.feeds["agent1.bsky.social"][0].uri == "uri1"
        assert result.feeds["agent1.bsky.social"][1].uri == "uri2"
        assert result.feeds["agent2.bsky.social"][0].uri == "uri3"

        # Verify repository calls
        mock_repos["run_repo"].get_run.assert_called_once_with(run_id)
        mock_repos["generated_feed_repo"].read_feeds_for_turn.assert_called_once_with(
            run_id, turn_number
        )
        mock_repos["feed_post_repo"].read_feed_posts_by_uris.assert_called_once()
        # Verify batch query was called with all URIs
        call_args = mock_repos["feed_post_repo"].read_feed_posts_by_uris.call_args[0][0]
        assert set(call_args) == {"uri1", "uri2", "uri3"}

    def test_returns_none_when_turn_does_not_exist(
        self, engine, mock_repos, sample_run, default_test_params
    ):
        """Test that get_turn_data returns None when turn doesn't exist (no feeds)."""
        # Arrange
        run_id = default_test_params["run_id"]
        turn_number = default_test_params["turn_number"]

        mock_repos["run_repo"].get_run.return_value = sample_run
        mock_repos["generated_feed_repo"].read_feeds_for_turn.return_value = []

        # Act
        result = engine.get_turn_data(run_id, turn_number)

        # Assert
        assert result is None
        mock_repos["run_repo"].get_run.assert_called_once_with(run_id)
        mock_repos["generated_feed_repo"].read_feeds_for_turn.assert_called_once_with(
            run_id, turn_number
        )
        # Should not call feed_post_repo when no feeds
        mock_repos["feed_post_repo"].read_feed_posts_by_uris.assert_not_called()

    def test_raises_value_error_for_empty_run_id(self, engine, mock_repos):
        """Test that get_turn_data raises ValueError for empty run_id."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="run_id cannot be empty"):
            engine.get_turn_data("", 0)

        # Verify repositories were not called
        mock_repos["run_repo"].get_run.assert_not_called()
        mock_repos["generated_feed_repo"].read_feeds_for_turn.assert_not_called()

    def test_raises_value_error_for_whitespace_only_run_id(self, engine, mock_repos):
        """Test that get_turn_data raises ValueError for whitespace-only run_id."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="run_id cannot be empty"):
            engine.get_turn_data("   ", 0)

        # Verify repositories were not called
        mock_repos["run_repo"].get_run.assert_not_called()
        mock_repos["generated_feed_repo"].read_feeds_for_turn.assert_not_called()

    def test_raises_value_error_for_negative_turn_number(self, engine, mock_repos):
        """Test that get_turn_data raises ValueError for negative turn_number."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="turn_number cannot be negative"):
            engine.get_turn_data("run_123", -1)

        # Verify repositories were not called
        mock_repos["run_repo"].get_run.assert_not_called()
        mock_repos["generated_feed_repo"].read_feeds_for_turn.assert_not_called()

    def test_raises_value_error_for_none_run_id(self, engine, mock_repos):
        """Test that get_turn_data raises ValueError for None run_id."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="run_id cannot be empty"):
            engine.get_turn_data(None, 0)  # type: ignore

        # Verify repositories were not called
        mock_repos["run_repo"].get_run.assert_not_called()
        mock_repos["generated_feed_repo"].read_feeds_for_turn.assert_not_called()

    def test_raises_value_error_for_none_turn_number(self, engine, mock_repos):
        """Test that get_turn_data raises ValueError for None turn_number."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError):
            engine.get_turn_data("run_123", None)  # type: ignore

        # Verify repositories were not called
        mock_repos["run_repo"].get_run.assert_not_called()
        mock_repos["generated_feed_repo"].read_feeds_for_turn.assert_not_called()

    def test_raises_run_not_found_error_when_run_does_not_exist(
        self, engine, mock_repos
    ):
        """Test that get_turn_data raises RunNotFoundError for non-existent run."""
        # Arrange
        run_id = "nonexistent_run"
        turn_number = 0
        mock_repos["run_repo"].get_run.return_value = None

        # Act & Assert
        with pytest.raises(RunNotFoundError) as exc_info:
            engine.get_turn_data(run_id, turn_number)

        assert exc_info.value.run_id == run_id
        mock_repos["run_repo"].get_run.assert_called_once_with(run_id)
        # Should not call other repositories
        mock_repos["generated_feed_repo"].read_feeds_for_turn.assert_not_called()
        mock_repos["feed_post_repo"].read_feed_posts_by_uris.assert_not_called()

    def test_handles_missing_posts_gracefully(
        self, engine, mock_repos, sample_run, sample_posts, default_test_params
    ):
        """Test that get_turn_data handles missing posts gracefully (skips missing, returns partial feeds)."""
        # Arrange
        run_id = default_test_params["run_id"]
        turn_number = default_test_params["turn_number"]

        feed = GeneratedFeed(
            feed_id="feed_1",
            run_id=run_id,
            turn_number=turn_number,
            agent_handle="agent1.bsky.social",
            post_uris=[
                "uri1",
                "uri2",
                "missing_uri",
            ],  # uri2 and missing_uri have no corresponding post objects in the repository (only uri1 does)
            created_at="2024_01_01-12:00:00",
        )

        # Only uri1 exists, uri2 and missing_uri don't
        mock_repos["run_repo"].get_run.return_value = sample_run
        mock_repos["generated_feed_repo"].read_feeds_for_turn.return_value = [feed]
        mock_repos["feed_post_repo"].read_feed_posts_by_uris.return_value = [
            sample_posts[0]
        ]  # Only first post

        # Act
        result = engine.get_turn_data(run_id, turn_number)

        # Assert
        assert result is not None
        assert len(result.feeds["agent1.bsky.social"]) == 1  # Only uri1 found
        assert result.feeds["agent1.bsky.social"][0].uri == "uri1"
        # Verify batch query was called with all URIs (including missing ones)
        call_args = mock_repos["feed_post_repo"].read_feed_posts_by_uris.call_args[0][0]
        assert set(call_args) == {"uri1", "uri2", "missing_uri"}

    def test_handles_empty_feeds_when_all_posts_missing(
        self, engine, mock_repos, sample_run, default_test_params
    ):
        """Test that get_turn_data returns TurnData with empty feeds dict when all posts missing."""
        # Arrange
        run_id = default_test_params["run_id"]
        turn_number = default_test_params["turn_number"]

        feed = GeneratedFeed(
            feed_id="feed_1",
            run_id=run_id,
            turn_number=turn_number,
            agent_handle="agent1.bsky.social",
            post_uris=["missing_uri1", "missing_uri2"],
            created_at="2024_01_01-12:00:00",
        )

        mock_repos["run_repo"].get_run.return_value = sample_run
        mock_repos["generated_feed_repo"].read_feeds_for_turn.return_value = [feed]
        # No posts found
        mock_repos["feed_post_repo"].read_feed_posts_by_uris.return_value = []

        # Act
        result = engine.get_turn_data(run_id, turn_number)

        # Assert
        assert result is not None
        assert result.turn_number == turn_number
        assert result.feeds["agent1.bsky.social"] == []  # Empty list, not None
        # Turn exists but data is incomplete

    def test_handles_multiple_feeds_with_overlapping_uris(
        self, engine, mock_repos, sample_run, default_test_params
    ):
        """Test that get_turn_data handles multiple feeds with overlapping post URIs correctly."""
        # Arrange
        run_id = default_test_params["run_id"]
        turn_number = default_test_params["turn_number"]

        # Two feeds with overlapping URIs
        feed1 = GeneratedFeed(
            feed_id="feed_1",
            run_id=run_id,
            turn_number=turn_number,
            agent_handle="agent1.bsky.social",
            post_uris=["uri1", "uri2"],  # uri2 is shared
            created_at="2024_01_01-12:00:00",
        )
        feed2 = GeneratedFeed(
            feed_id="feed_2",
            run_id=run_id,
            turn_number=turn_number,
            agent_handle="agent2.bsky.social",
            post_uris=["uri2", "uri3"],  # uri2 is shared
            created_at="2024_01_01-12:01:00",
        )

        post1 = BlueskyFeedPost(
            id="uri1",
            uri="uri1",
            author_display_name="Author 1",
            author_handle="author1.bsky.social",
            text="Post 1",
            bookmark_count=0,
            like_count=0,
            quote_count=0,
            reply_count=0,
            repost_count=0,
            created_at="2024_01_01-12:00:00",
        )
        post2 = BlueskyFeedPost(
            id="uri2",
            uri="uri2",
            author_display_name="Author 2",
            author_handle="author2.bsky.social",
            text="Post 2",
            bookmark_count=0,
            like_count=0,
            quote_count=0,
            reply_count=0,
            repost_count=0,
            created_at="2024_01_01-12:01:00",
        )
        post3 = BlueskyFeedPost(
            id="uri3",
            uri="uri3",
            author_display_name="Author 3",
            author_handle="author3.bsky.social",
            text="Post 3",
            bookmark_count=0,
            like_count=0,
            quote_count=0,
            reply_count=0,
            repost_count=0,
            created_at="2024_01_01-12:02:00",
        )

        mock_repos["run_repo"].get_run.return_value = sample_run
        mock_repos["generated_feed_repo"].read_feeds_for_turn.return_value = [
            feed1,
            feed2,
        ]
        mock_repos["feed_post_repo"].read_feed_posts_by_uris.return_value = [
            post1,
            post2,
            post3,
        ]

        # Act
        result = engine.get_turn_data(run_id, turn_number)

        # Assert
        assert result is not None
        assert len(result.feeds) == 2
        assert len(result.feeds["agent1.bsky.social"]) == 2  # uri1, uri2
        assert len(result.feeds["agent2.bsky.social"]) == 2  # uri2, uri3
        # Verify batch query was called with unique URIs only (uri1, uri2, uri3)
        call_args = mock_repos["feed_post_repo"].read_feed_posts_by_uris.call_args[0][0]
        assert set(call_args) == {"uri1", "uri2", "uri3"}
        assert len(call_args) == 3  # No duplicates

    def test_repository_exceptions_propagate(
        self, engine, mock_repos, sample_run, default_test_params
    ):
        """Test that repository exceptions propagate without wrapping."""
        # Arrange
        run_id = default_test_params["run_id"]
        turn_number = default_test_params["turn_number"]

        original_error = RuntimeError("Database connection failed")
        mock_repos["run_repo"].get_run.return_value = sample_run
        mock_repos[
            "generated_feed_repo"
        ].read_feeds_for_turn.side_effect = original_error

        # Act & Assert
        with pytest.raises(RuntimeError) as exc_info:
            engine.get_turn_data(run_id, turn_number)

        # Verify it's the same exception (not wrapped)
        assert exc_info.value is original_error
        mock_repos["run_repo"].get_run.assert_called_once_with(run_id)
        mock_repos["generated_feed_repo"].read_feeds_for_turn.assert_called_once_with(
            run_id, turn_number
        )


class TestSimulationEngineUpdateRunStatusSafely:
    """Tests for SimulationEngine._update_run_status_safely method."""

    def test_updates_status_successfully(self, engine, mock_repos):
        """Test that _update_run_status_safely updates status when repository call succeeds."""
        # Arrange
        run_id = "run_123"
        status = RunStatus.COMPLETED
        mock_repos["run_repo"].update_run_status.return_value = None

        # Act
        engine._update_run_status_safely(run_id, status)

        # Assert
        mock_repos["run_repo"].update_run_status.assert_called_once_with(run_id, status)

    def test_logs_warning_and_does_not_raise_on_failure(self, engine, mock_repos):
        """Test that _update_run_status_safely logs warning and doesn't raise when repository fails."""
        # Arrange
        run_id = "run_123"
        status = RunStatus.FAILED
        original_error = RunStatusUpdateError(run_id, "Database connection failed")
        mock_repos["run_repo"].update_run_status.side_effect = original_error

        # Act & Assert - should not raise
        with patch("simulation.core.engine.logger") as mock_logger:
            engine._update_run_status_safely(run_id, status)

            # Verify warning was logged
            mock_logger.warning.assert_called_once()
            log_call_args = mock_logger.warning.call_args[0][0]
            assert f"Failed to update run {run_id} status to {status}" in log_call_args
            assert str(original_error) in log_call_args

        # Verify repository was called
        mock_repos["run_repo"].update_run_status.assert_called_once_with(run_id, status)

    def test_handles_generic_exception_gracefully(self, engine, mock_repos):
        """Test that _update_run_status_safely handles any exception type without raising."""
        # Arrange
        run_id = "run_123"
        status = RunStatus.COMPLETED
        generic_error = RuntimeError("Unexpected error")
        mock_repos["run_repo"].update_run_status.side_effect = generic_error

        # Act & Assert - should not raise
        with patch("simulation.core.engine.logger") as mock_logger:
            engine._update_run_status_safely(run_id, status)

            # Verify warning was logged
            mock_logger.warning.assert_called_once()
            log_call_args = mock_logger.warning.call_args[0][0]
            assert f"Failed to update run {run_id} status to {status}" in log_call_args
            assert str(generic_error) in log_call_args

        # Verify repository was called
        mock_repos["run_repo"].update_run_status.assert_called_once_with(run_id, status)

    def test_handles_database_connection_error_gracefully(self, engine, mock_repos):
        """Test that _update_run_status_safely handles database connection errors without raising."""
        # Arrange
        run_id = "run_123"
        status = RunStatus.FAILED
        db_error = ConnectionError("Database connection lost")
        mock_repos["run_repo"].update_run_status.side_effect = db_error

        # Act & Assert - should not raise
        with patch("simulation.core.engine.logger") as mock_logger:
            engine._update_run_status_safely(run_id, status)

            # Verify warning was logged
            mock_logger.warning.assert_called_once()
            log_call_args = mock_logger.warning.call_args[0][0]
            assert f"Failed to update run {run_id} status to {status}" in log_call_args

        # Verify repository was called
        mock_repos["run_repo"].update_run_status.assert_called_once_with(run_id, status)

    def test_can_be_called_multiple_times_after_failure(self, engine, mock_repos):
        """Test that _update_run_status_safely can be called again after a failure."""
        # Arrange
        run_id = "run_123"
        status = RunStatus.FAILED
        mock_repos["run_repo"].update_run_status.side_effect = [
            RunStatusUpdateError(run_id, "First failure"),
            None,  # Second call succeeds
        ]

        # Act
        with patch("simulation.core.engine.logger") as mock_logger:
            # First call fails
            engine._update_run_status_safely(run_id, status)
            # Second call succeeds
            engine._update_run_status_safely(run_id, RunStatus.COMPLETED)

            # Verify warning was logged once (for first failure)
            assert mock_logger.warning.call_count == 1

        # Verify repository was called twice
        assert mock_repos["run_repo"].update_run_status.call_count == 2
