"""Tests for simulation.core.query_service module."""

from unittest.mock import Mock

import pytest

from db.repositories.feed_post_repository import FeedPostRepository
from db.repositories.generated_feed_repository import GeneratedFeedRepository
from db.repositories.run_repository import RunRepository
from simulation.core.exceptions import RunNotFoundError
from simulation.core.models.feeds import GeneratedFeed
from simulation.core.models.posts import BlueskyFeedPost
from simulation.core.models.runs import Run, RunStatus
from simulation.core.models.turns import TurnData, TurnMetadata
from simulation.core.query_service import SimulationQueryService


@pytest.fixture
def mock_repos():
    return {
        "run_repo": Mock(spec=RunRepository),
        "feed_post_repo": Mock(spec=FeedPostRepository),
        "generated_feed_repo": Mock(spec=GeneratedFeedRepository),
    }


@pytest.fixture
def query_service(mock_repos):
    return SimulationQueryService(
        run_repo=mock_repos["run_repo"],
        feed_post_repo=mock_repos["feed_post_repo"],
        generated_feed_repo=mock_repos["generated_feed_repo"],
    )


@pytest.fixture
def sample_run():
    return Run(
        run_id="run_123",
        created_at="2024_01_01-12:00:00",
        total_turns=10,
        total_agents=5,
        started_at="2024_01_01-12:00:00",
        status=RunStatus.RUNNING,
        completed_at=None,
    )


class TestSimulationQueryServiceGetRun:
    def test_returns_run_when_found(self, query_service, mock_repos, sample_run):
        mock_repos["run_repo"].get_run.return_value = sample_run
        result = query_service.get_run(sample_run.run_id)
        assert result == sample_run
        mock_repos["run_repo"].get_run.assert_called_once_with(sample_run.run_id)

    def test_raises_value_error_for_empty_id(self, query_service):
        with pytest.raises(ValueError, match="run_id cannot be empty"):
            query_service.get_run("")


class TestSimulationQueryServiceListRuns:
    def test_returns_runs(self, query_service, mock_repos, sample_run):
        mock_repos["run_repo"].list_runs.return_value = [sample_run]
        result = query_service.list_runs()
        assert result == [sample_run]
        mock_repos["run_repo"].list_runs.assert_called_once()


class TestSimulationQueryServiceGetTurnMetadata:
    def test_returns_metadata(self, query_service, mock_repos):
        expected = TurnMetadata(
            run_id="run_123",
            turn_number=0,
            total_actions={},
            created_at="2024_01_01-12:00:00",
        )
        mock_repos["run_repo"].get_turn_metadata.return_value = expected

        result = query_service.get_turn_metadata("run_123", 0)
        assert result == expected
        mock_repos["run_repo"].get_turn_metadata.assert_called_once_with("run_123", 0)

    def test_validates_turn_number(self, query_service):
        with pytest.raises(ValueError, match="turn_number must be >= 0"):
            query_service.get_turn_metadata("run_123", -1)


class TestSimulationQueryServiceListTurnMetadata:
    def test_returns_turn_metadata_list(self, query_service, mock_repos):
        expected_result = [
            TurnMetadata(
                run_id="run_123",
                turn_number=0,
                total_actions={},
                created_at="2024_01_01-12:00:00",
            ),
            TurnMetadata(
                run_id="run_123",
                turn_number=1,
                total_actions={},
                created_at="2024_01_01-12:01:00",
            ),
        ]
        mock_repos["run_repo"].list_turn_metadata.return_value = expected_result

        result = query_service.list_turn_metadata("run_123")

        assert result == expected_result
        mock_repos["run_repo"].list_turn_metadata.assert_called_once_with(
            run_id="run_123"
        )

    def test_validates_run_id(self, query_service, mock_repos):
        with pytest.raises(ValueError, match="run_id cannot be empty"):
            query_service.list_turn_metadata("")

        mock_repos["run_repo"].list_turn_metadata.assert_not_called()


class TestSimulationQueryServiceGetTurnData:
    def test_returns_turn_data_with_feeds_and_posts(
        self, query_service, mock_repos, sample_run
    ):
        feed1 = GeneratedFeed(
            feed_id="feed_1",
            run_id=sample_run.run_id,
            turn_number=0,
            agent_handle="agent1.bsky.social",
            post_uris=["uri1", "uri2"],
            created_at="2024_01_01-12:00:00",
        )
        feed2 = GeneratedFeed(
            feed_id="feed_2",
            run_id=sample_run.run_id,
            turn_number=0,
            agent_handle="agent2.bsky.social",
            post_uris=["uri3"],
            created_at="2024_01_01-12:00:01",
        )
        posts = [
            BlueskyFeedPost(
                id="uri1",
                uri="uri1",
                author_display_name="Author 1",
                author_handle="author1.bsky.social",
                text="Post 1",
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
                text="Post 2",
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
                text="Post 3",
                bookmark_count=0,
                like_count=0,
                quote_count=0,
                reply_count=0,
                repost_count=0,
                created_at="2024_01_01-12:02:00",
            ),
        ]
        mock_repos["run_repo"].get_run.return_value = sample_run
        mock_repos["generated_feed_repo"].read_feeds_for_turn.return_value = [
            feed1,
            feed2,
        ]
        mock_repos["feed_post_repo"].read_feed_posts_by_uris.return_value = posts

        result = query_service.get_turn_data(sample_run.run_id, 0)

        assert isinstance(result, TurnData)
        assert result is not None
        assert len(result.feeds["agent1.bsky.social"]) == 2
        assert len(result.feeds["agent2.bsky.social"]) == 1

    def test_raises_run_not_found(self, query_service, mock_repos):
        mock_repos["run_repo"].get_run.return_value = None
        with pytest.raises(RunNotFoundError):
            query_service.get_turn_data("missing", 0)

    def test_returns_none_when_no_feeds(self, query_service, mock_repos, sample_run):
        mock_repos["run_repo"].get_run.return_value = sample_run
        mock_repos["generated_feed_repo"].read_feeds_for_turn.return_value = []
        assert query_service.get_turn_data(sample_run.run_id, 0) is None
