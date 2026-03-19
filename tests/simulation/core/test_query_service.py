"""Tests for simulation.core.services.query_service module."""

from unittest.mock import Mock

import pytest

from simulation.core.models.generated.like import GeneratedLike
from simulation.core.models.turns import TurnData
from simulation.core.services.query_service import SimulationQueryService
from simulation.core.utils.exceptions import RunNotFoundError
from tests.factories import (
    AgentRecordFactory,
    GeneratedFeedFactory,
    PersistedLikeFactory,
    RunAgentSnapshotFactory,
    RunConfigFactory,
    RunPostSnapshotFactory,
    TurnMetadataFactory,
)

SAMPLE_RUN_OVERRIDES = {"total_turns": 10, "total_agents": 5}


@pytest.fixture
def query_service(mock_repos):
    return SimulationQueryService(
        run_repo=mock_repos["run_repo"],
        metrics_repo=mock_repos["metrics_repo"],
        run_post_repo=mock_repos["run_post_repo"],
        run_post_like_repo=mock_repos["run_post_like_repo"],
        generated_feed_repo=mock_repos["generated_feed_repo"],
        like_repo=mock_repos["like_repo"],
        comment_repo=mock_repos["comment_repo"],
        follow_repo=mock_repos["follow_repo"],
        run_follow_edge_repo=mock_repos["run_follow_edge_repo"],
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
        expected = TurnMetadataFactory.create(
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
            TurnMetadataFactory.create(
                run_id="run_123",
                turn_number=0,
                total_actions={},
                created_at="2024_01_01-12:00:00",
            ),
            TurnMetadataFactory.create(
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

    def test_sorts_turn_metadata_by_turn_number(self, query_service, mock_repos):
        unsorted_metadata = [
            TurnMetadataFactory.create(
                run_id="run_123",
                turn_number=2,
                total_actions={},
                created_at="2024_01_01-12:02:00",
            ),
            TurnMetadataFactory.create(
                run_id="run_123",
                turn_number=0,
                total_actions={},
                created_at="2024_01_01-12:00:00",
            ),
            TurnMetadataFactory.create(
                run_id="run_123",
                turn_number=1,
                total_actions={},
                created_at="2024_01_01-12:01:00",
            ),
        ]
        mock_repos["run_repo"].list_turn_metadata.return_value = unsorted_metadata

        result = query_service.list_turn_metadata("run_123")

        expected_turn_numbers = [0, 1, 2]
        assert [item.turn_number for item in result] == expected_turn_numbers

    def test_validates_run_id(self, query_service, mock_repos):
        with pytest.raises(ValueError, match="run_id cannot be empty"):
            query_service.list_turn_metadata("")

        mock_repos["run_repo"].list_turn_metadata.assert_not_called()


class TestSimulationQueryServiceGetTurnData:
    def test_returns_turn_data_with_feeds_and_posts(
        self, query_service, mock_repos, sample_run
    ):
        feed1 = GeneratedFeedFactory.create(
            feed_id="feed_1",
            run_id=sample_run.run_id,
            turn_number=0,
            agent_handle="agent1.bsky.social",
            post_ids=["rp_1", "rp_2"],
            created_at="2024_01_01-12:00:00",
        )
        feed2 = GeneratedFeedFactory.create(
            feed_id="feed_2",
            run_id=sample_run.run_id,
            turn_number=0,
            agent_handle="agent2.bsky.social",
            post_ids=["rp_3"],
            created_at="2024_01_01-12:00:01",
        )
        run_post_snapshots = [
            RunPostSnapshotFactory.create(
                run_post_id="rp_1",
                run_id=sample_run.run_id,
                author_handle_at_start="author1.bsky.social",
                author_display_name_at_start="Author 1",
                body_text_at_start="Post 1",
                published_at_start="2024_01_01-12:00:00",
            ),
            RunPostSnapshotFactory.create(
                run_post_id="rp_2",
                run_id=sample_run.run_id,
                author_handle_at_start="author2.bsky.social",
                author_display_name_at_start="Author 2",
                body_text_at_start="Post 2",
                published_at_start="2024_01_01-12:01:00",
            ),
            RunPostSnapshotFactory.create(
                run_post_id="rp_3",
                run_id=sample_run.run_id,
                author_handle_at_start="author3.bsky.social",
                author_display_name_at_start="Author 3",
                body_text_at_start="Post 3",
                published_at_start="2024_01_01-12:02:00",
            ),
        ]
        mock_repos["run_repo"].get_run.return_value = sample_run
        mock_repos["generated_feed_repo"].read_feeds_for_turn.return_value = [
            feed1,
            feed2,
        ]
        mock_repos[
            "run_post_repo"
        ].read_run_posts_by_ids.return_value = run_post_snapshots

        result = query_service.get_turn_data(sample_run.run_id, 0)

        assert isinstance(result, TurnData)
        assert result is not None
        assert len(result.feeds["agent1.bsky.social"]) == 2
        assert len(result.feeds["agent2.bsky.social"]) == 1
        call_args = mock_repos["run_post_repo"].read_run_posts_by_ids.call_args
        assert call_args[0][0] == sample_run.run_id
        assert set(call_args[0][1]) == {"rp_1", "rp_2", "rp_3"}
        # Verify post hydration from run_post_repo: content comes from RunPostSnapshot
        posts_agent1 = result.feeds["agent1.bsky.social"]
        assert posts_agent1[0].post_id == "rp_1"
        assert posts_agent1[0].text == "Post 1"
        assert posts_agent1[0].author_handle == "author1.bsky.social"
        assert posts_agent1[1].post_id == "rp_2"
        assert posts_agent1[1].text == "Post 2"
        posts_agent2 = result.feeds["agent2.bsky.social"]
        assert posts_agent2[0].post_id == "rp_3"
        assert posts_agent2[0].text == "Post 3"

    def test_raises_run_not_found(self, query_service, mock_repos):
        mock_repos["run_repo"].get_run.return_value = None
        with pytest.raises(RunNotFoundError):
            query_service.get_turn_data("missing", 0)

    def test_returns_none_when_no_feeds(self, query_service, mock_repos, sample_run):
        mock_repos["run_repo"].get_run.return_value = sample_run
        mock_repos["generated_feed_repo"].read_feeds_for_turn.return_value = []
        assert query_service.get_turn_data(sample_run.run_id, 0) is None

    def test_get_turn_data_hydrates_actions_from_action_repos(
        self, mock_repos, sample_run
    ):
        """When like/comment/follow repos are provided, get_turn_data populates actions."""
        like_repo = Mock()
        like_repo.read_likes_by_run_turn.return_value = [
            PersistedLikeFactory.create(
                like_id="like_1",
                run_id=sample_run.run_id,
                turn_number=0,
                agent_handle="agent1.bsky.social",
                post_id="rp_post1",
                created_at="2026-02-24T12:00:00Z",
                explanation="Great",
                model_used=None,
                generation_metadata_json=None,
                generation_created_at=None,
            )
        ]
        comment_repo = Mock()
        comment_repo.read_comments_by_run_turn.return_value = []
        follow_repo = Mock()
        follow_repo.read_follows_by_run_turn.return_value = []

        query_service = SimulationQueryService(
            run_repo=mock_repos["run_repo"],
            metrics_repo=mock_repos["metrics_repo"],
            run_post_repo=mock_repos["run_post_repo"],
            run_post_like_repo=mock_repos["run_post_like_repo"],
            generated_feed_repo=mock_repos["generated_feed_repo"],
            like_repo=like_repo,
            comment_repo=comment_repo,
            follow_repo=follow_repo,
            run_follow_edge_repo=mock_repos["run_follow_edge_repo"],
        )
        feed = GeneratedFeedFactory.create(
            feed_id="f1",
            run_id=sample_run.run_id,
            turn_number=0,
            agent_handle="agent1.bsky.social",
            post_ids=["rp_post1"],
            created_at="2026-02-24T12:00:00Z",
        )
        run_post = RunPostSnapshotFactory.create(
            run_post_id="rp_post1",
            run_id=sample_run.run_id,
            author_display_name_at_start="Author",
            author_handle_at_start="author.bsky.social",
            body_text_at_start="Hello",
            published_at_start="2026-02-24T12:00:00",
        )
        mock_repos["run_repo"].get_run.return_value = sample_run
        mock_repos["generated_feed_repo"].read_feeds_for_turn.return_value = [feed]
        mock_repos["run_post_repo"].read_run_posts_by_ids.return_value = [run_post]

        result = query_service.get_turn_data(sample_run.run_id, 0)

        assert result is not None
        assert "agent1.bsky.social" in result.actions
        agent_actions = result.actions["agent1.bsky.social"]
        assert len(agent_actions) == 1
        assert isinstance(agent_actions[0], GeneratedLike)
        assert agent_actions[0].like.like_id == "like_1"
        assert agent_actions[0].like.post_id == "rp_post1"
        like_repo.read_likes_by_run_turn.assert_called_once_with(sample_run.run_id, 0)


class TestSimulationQueryServiceRunPostIsolation:
    """Isolation: run A shows original post set after run B created with different seed."""

    def test_run_a_shows_original_posts_after_run_b_has_different_posts(
        self,
        run_repo,
        run_post_repo,
        generated_feed_repo,
        run_agent_repo,
        agent_repo,
        like_repo,
        comment_repo,
        follow_repo,
        run_follow_edge_repo,
        metrics_repo,
        mock_repos,
    ):
        from simulation.core.models.feeds import GeneratedFeed

        run_a = run_repo.create_run(
            RunConfigFactory.create(
                num_agents=1, num_turns=1, feed_algorithm="chronological"
            )
        )
        run_b = run_repo.create_run(
            RunConfigFactory.create(
                num_agents=1, num_turns=1, feed_algorithm="chronological"
            )
        )

        agent_repo.create_or_update_agent(
            AgentRecordFactory.create(
                agent_id="did:plc:agent1",
                handle="agent1.bsky.social",
                display_name="Agent One",
                created_at="2026-03-17T00:00:00Z",
                updated_at="2026-03-17T00:00:00Z",
            )
        )
        run_agent_repo.write_run_agents(
            run_a.run_id,
            [
                RunAgentSnapshotFactory.create(
                    run_id=run_a.run_id,
                    agent_id="did:plc:agent1",
                    selection_order=0,
                    handle_at_start="agent1.bsky.social",
                )
            ],
        )
        run_agent_repo.write_run_agents(
            run_b.run_id,
            [
                RunAgentSnapshotFactory.create(
                    run_id=run_b.run_id,
                    agent_id="did:plc:agent1",
                    selection_order=0,
                    handle_at_start="agent1.bsky.social",
                )
            ],
        )

        run_posts_a = [
            RunPostSnapshotFactory.create(
                run_post_id="rp_a1",
                run_id=run_a.run_id,
                author_agent_id="did:plc:agent1",
                author_handle_at_start="agent1.bsky.social",
                author_display_name_at_start="Agent One",
                body_text_at_start="Original post for run A",
                published_at_start="2026-03-17T10:00:00Z",
                created_at=run_a.created_at,
            ),
        ]
        run_posts_b = [
            RunPostSnapshotFactory.create(
                run_post_id="rp_b1",
                run_id=run_b.run_id,
                author_agent_id="did:plc:agent1",
                author_handle_at_start="agent1.bsky.social",
                author_display_name_at_start="Agent One",
                body_text_at_start="Different post for run B",
                published_at_start="2026-03-17T11:00:00Z",
                created_at=run_b.created_at,
            ),
        ]
        run_post_repo.write_run_posts(run_a.run_id, run_posts_a)
        run_post_repo.write_run_posts(run_b.run_id, run_posts_b)

        feed_a = GeneratedFeed(
            feed_id="f_a",
            run_id=run_a.run_id,
            turn_number=0,
            agent_handle="agent1.bsky.social",
            post_ids=["rp_a1"],
            created_at="2026-03-17T10:00:00Z",
        )
        feed_b = GeneratedFeed(
            feed_id="f_b",
            run_id=run_b.run_id,
            turn_number=0,
            agent_handle="agent1.bsky.social",
            post_ids=["rp_b1"],
            created_at="2026-03-17T11:00:00Z",
        )
        generated_feed_repo.write_generated_feed(feed_a)
        generated_feed_repo.write_generated_feed(feed_b)

        query_service = SimulationQueryService(
            run_repo=run_repo,
            metrics_repo=metrics_repo,
            run_post_repo=run_post_repo,
            run_post_like_repo=mock_repos["run_post_like_repo"],
            generated_feed_repo=generated_feed_repo,
            like_repo=like_repo,
            comment_repo=comment_repo,
            follow_repo=follow_repo,
            run_follow_edge_repo=run_follow_edge_repo,
        )

        turn_data_a = query_service.get_turn_data(run_a.run_id, 0)
        turn_data_b = query_service.get_turn_data(run_b.run_id, 0)

        assert turn_data_a is not None
        assert turn_data_b is not None
        assert (
            turn_data_a.feeds["agent1.bsky.social"][0].text == "Original post for run A"
        )
        assert (
            turn_data_b.feeds["agent1.bsky.social"][0].text
            == "Different post for run B"
        )


class TestSimulationQueryServiceRunFollowEdges:
    def test_lists_run_follow_edges(self, query_service, mock_repos):
        expected = [Mock()]
        mock_repos["run_follow_edge_repo"].list_run_follow_edges.return_value = expected

        result = query_service.list_run_follow_edges("run_123")

        assert result == expected
        mock_repos[
            "run_follow_edge_repo"
        ].list_run_follow_edges.assert_called_once_with("run_123")
