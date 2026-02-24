"""Tests for simulation.core.command_service module."""

from unittest.mock import Mock, patch

import pytest

from db.services.simulation_persistence_service import SimulationPersistenceService
from feeds.interfaces import FeedGenerator
from simulation.core.action_history import InMemoryActionHistoryStore
from simulation.core.agent_action_feed_filter import (
    ActionCandidateFeeds,
    HistoryAwareActionFeedFilter,
)
from simulation.core.agent_action_history_recorder import AgentActionHistoryRecorder
from simulation.core.agent_action_rules_validator import AgentActionRulesValidator
from simulation.core.command_service import SimulationCommandService
from simulation.core.exceptions import RunStatusUpdateError, SimulationRunFailure
from simulation.core.metrics.collector import MetricsCollector
from simulation.core.metrics.defaults import DEFAULT_TURN_METRIC_KEYS
from simulation.core.models.actions import Comment, Follow, Like, TurnAction
from simulation.core.models.agents import SocialMediaAgent
from simulation.core.models.generated.base import GenerationMetadata
from simulation.core.models.generated.comment import GeneratedComment
from simulation.core.models.generated.follow import GeneratedFollow
from simulation.core.models.generated.like import GeneratedLike
from simulation.core.models.posts import BlueskyFeedPost
from simulation.core.models.runs import RunStatus
from simulation.core.models.turns import TurnResult


@pytest.fixture
def mock_agent_factory():
    factory = Mock()
    factory.side_effect = lambda num_agents: [
        SocialMediaAgent(f"agent{i}.bsky.social") for i in range(num_agents)
    ]
    return factory


@pytest.fixture
def mock_feed_generator():
    """Feed generator mock that returns one empty feed per agent (satisfies validate_agents_without_feeds)."""
    mock = Mock(spec=FeedGenerator)
    mock.generate_feeds.side_effect = (
        lambda agents, run_id, turn_number, feed_algorithm, feed_algorithm_config=None: {
            a.handle: [] for a in agents
        }
    )
    return mock


@pytest.fixture
def command_service(mock_repos, mock_agent_factory, mock_feed_generator):
    action_history_store = Mock()
    action_history_store.has_liked.return_value = False
    action_history_store.has_commented.return_value = False
    action_history_store.has_followed.return_value = False
    action_history_store_factory = Mock(return_value=action_history_store)
    agent_action_feed_filter = Mock()
    agent_action_feed_filter.filter_candidates.side_effect = lambda **kwargs: (
        ActionCandidateFeeds(
            like_candidates=kwargs["feed"],
            comment_candidates=kwargs["feed"],
            follow_candidates=kwargs["feed"],
        )
    )
    agent_action_rules_validator = Mock(spec=AgentActionRulesValidator)
    agent_action_rules_validator.validate.return_value = ([], [], [])
    agent_action_history_recorder = Mock(spec=AgentActionHistoryRecorder)
    metrics_collector = Mock(spec=MetricsCollector)
    metrics_collector.collect_turn_metrics.return_value = {}
    metrics_collector.collect_run_metrics.return_value = {}
    simulation_persistence = Mock(spec=SimulationPersistenceService)
    return SimulationCommandService(
        run_repo=mock_repos["run_repo"],
        metrics_repo=mock_repos["metrics_repo"],
        metrics_collector=metrics_collector,
        simulation_persistence=simulation_persistence,
        profile_repo=mock_repos["profile_repo"],
        feed_post_repo=mock_repos["feed_post_repo"],
        generated_bio_repo=mock_repos["generated_bio_repo"],
        generated_feed_repo=mock_repos["generated_feed_repo"],
        agent_factory=mock_agent_factory,
        action_history_store_factory=action_history_store_factory,
        feed_generator=mock_feed_generator,
        agent_action_rules_validator=agent_action_rules_validator,
        agent_action_history_recorder=agent_action_history_recorder,
        agent_action_feed_filter=agent_action_feed_filter,
    )


class TestSimulationCommandServiceUpdateRunStatus:
    def test_updates_status_successfully(self, command_service, mock_repos, sample_run):
        command_service.update_run_status(sample_run, RunStatus.COMPLETED)
        mock_repos["run_repo"].update_run_status.assert_called_once_with(
            sample_run.run_id, RunStatus.COMPLETED
        )

    def test_retries_then_succeeds(self, command_service, mock_repos, sample_run):
        mock_repos["run_repo"].update_run_status.side_effect = [
            RunStatusUpdateError(sample_run.run_id, "first"),
            RunStatusUpdateError(sample_run.run_id, "second"),
            None,
        ]
        with patch("simulation.core.command_service.time.sleep") as mock_sleep:
            command_service.update_run_status(sample_run, RunStatus.RUNNING)
        assert mock_repos["run_repo"].update_run_status.call_count == 3
        assert mock_sleep.call_count == 2


class TestSimulationCommandServiceExecuteRun:
    def _make_config(self, turns: int = 2):
        return type(
            "Cfg",
            (),
            {
                "feed_algorithm": "chronological",
                "num_agents": 2,
                "num_turns": turns,
                "feed_algorithm_config": None,
                "metric_keys": [
                    "run.actions.total",
                    "run.actions.total_by_type",
                    "turn.actions.counts_by_type",
                    "turn.actions.total",
                ],
            },
        )()

    def test_success_path(
        self, command_service, mock_repos, sample_run, mock_agent_factory
    ):
        mock_repos["run_repo"].create_run.return_value = sample_run
        mock_repos["run_repo"].update_run_status.return_value = None
        mock_agent_factory.return_value = [
            SocialMediaAgent("agent1.bsky.social"),
            SocialMediaAgent("agent2.bsky.social"),
        ]

        with patch(
            "simulation.core.command_service.SimulationCommandService._simulate_turn"
        ) as mock_sim_turn:
            mock_sim_turn.side_effect = [
                TurnResult(turn_number=0, total_actions={}, execution_time_ms=10),
                TurnResult(turn_number=1, total_actions={}, execution_time_ms=12),
            ]
            result = command_service.execute_run(self._make_config())

        assert result == sample_run
        assert mock_sim_turn.call_count == 2
        # RUNNING at start; COMPLETED is set inside write_run (persistence layer)
        mock_repos["run_repo"].update_run_status.assert_called_once_with(
            sample_run.run_id, RunStatus.RUNNING
        )
        command_service.simulation_persistence.write_run.assert_called_once()
        call_args = command_service.simulation_persistence.write_run.call_args
        assert call_args[0][0] == sample_run.run_id
        assert call_args[0][1].run_id == sample_run.run_id

    def test_run_creation_failure_raises_simulation_run_failure_with_no_run_id(
        self, command_service, mock_repos
    ):
        mock_repos["run_repo"].create_run.side_effect = RuntimeError("db error")

        with pytest.raises(SimulationRunFailure) as exc_info:
            command_service.execute_run(self._make_config(turns=1))

        assert exc_info.value.run_id is None
        mock_repos["run_repo"].update_run_status.assert_not_called()

    def test_agent_creation_failure_marks_failed(
        self, command_service, mock_repos, sample_run, mock_agent_factory
    ):
        mock_repos["run_repo"].create_run.return_value = sample_run
        mock_repos["run_repo"].update_run_status.return_value = None
        mock_agent_factory.side_effect = RuntimeError("agent failure")

        with pytest.raises(SimulationRunFailure) as exc_info:
            command_service.execute_run(self._make_config(turns=1))

        assert exc_info.value.run_id == sample_run.run_id
        calls = mock_repos["run_repo"].update_run_status.call_args_list
        assert calls[0][0] == (sample_run.run_id, RunStatus.RUNNING)
        assert calls[1][0] == (sample_run.run_id, RunStatus.FAILED)

    def test_policy_violation_during_turn_marks_failed(
        self, command_service, mock_repos, sample_run, mock_agent_factory
    ):
        mock_repos["run_repo"].create_run.return_value = sample_run
        mock_repos["run_repo"].update_run_status.return_value = None
        mock_agent_factory.return_value = [SocialMediaAgent("agent1.bsky.social")]

        with patch(
            "simulation.core.command_service.SimulationCommandService._simulate_turn",
            side_effect=ValueError("invariant violation"),
        ):
            with pytest.raises(SimulationRunFailure) as exc_info:
                command_service.execute_run(self._make_config(turns=1))

        assert exc_info.value.run_id == sample_run.run_id
        calls = mock_repos["run_repo"].update_run_status.call_args_list
        assert calls[0][0] == (sample_run.run_id, RunStatus.RUNNING)
        assert calls[1][0] == (sample_run.run_id, RunStatus.FAILED)

    def test_simulate_turn_aggregates_actions_when_policy_passes(
        self, command_service, mock_repos, sample_run
    ):
        command_service.agent_action_rules_validator = Mock()
        command_service.agent_action_history_recorder = Mock()
        agent = SocialMediaAgent("agent1.bsky.social")
        feed_post = BlueskyFeedPost(
            id="post_1",
            uri="post_1",
            author_display_name="Author",
            author_handle="author.bsky.social",
            text="hello",
            bookmark_count=0,
            like_count=0,
            quote_count=0,
            reply_count=0,
            repost_count=0,
            created_at="2024_01_01-12:00:00",
        )

        metadata = GenerationMetadata(created_at="2024_01_01-12:00:00")
        agent.like_posts = Mock(
            return_value=[
                GeneratedLike(
                    like=Like(
                        like_id="like_1",
                        agent_id=agent.handle,
                        post_id="post_1",
                        created_at="2024_01_01-12:00:00",
                    ),
                    explanation="reason",
                    metadata=metadata,
                )
            ]
        )
        agent.comment_posts = Mock(
            return_value=[
                GeneratedComment(
                    comment=Comment(
                        comment_id="comment_1",
                        agent_id=agent.handle,
                        post_id="post_1",
                        text="nice post",
                        created_at="2024_01_01-12:00:00",
                    ),
                    explanation="reason",
                    metadata=metadata,
                )
            ]
        )
        agent.follow_users = Mock(
            return_value=[
                GeneratedFollow(
                    follow=Follow(
                        follow_id="follow_1",
                        agent_id=agent.handle,
                        user_id="user_1",
                        created_at="2024_01_01-12:00:00",
                    ),
                    explanation="reason",
                    metadata=metadata,
                )
            ]
        )

        mock_repos["run_repo"].get_run.return_value = sample_run
        command_service.agent_action_rules_validator.validate.return_value = (
            ["post_1"],
            ["post_1"],
            ["user_1"],
        )
        command_service.feed_generator.generate_feeds.return_value = {
            agent.handle: [feed_post]
        }
        command_service.feed_generator.generate_feeds.side_effect = None

        action_history_store = Mock()
        result = command_service._simulate_turn(
            run_id=sample_run.run_id,
            turn_number=0,
            agents=[agent],
            feed_algorithm="chronological",
            action_history_store=action_history_store,
            turn_metric_keys=DEFAULT_TURN_METRIC_KEYS,
        )

        assert result.total_actions[TurnAction.LIKE] == 1
        assert result.total_actions[TurnAction.COMMENT] == 1
        assert result.total_actions[TurnAction.FOLLOW] == 1
        command_service.agent_action_rules_validator.validate.assert_called_once()
        command_service.agent_action_history_recorder.record.assert_called_once()

    def test_simulate_turn_uses_action_specific_filtered_candidates(
        self, command_service, mock_repos, sample_run
    ):
        agent = SocialMediaAgent("agent1.bsky.social")
        like_only_post = BlueskyFeedPost(
            id="post_like",
            uri="post_like",
            author_display_name="Author A",
            author_handle="author-a.bsky.social",
            text="for likes",
            bookmark_count=0,
            like_count=0,
            quote_count=0,
            reply_count=0,
            repost_count=0,
            created_at="2024_01_01-12:00:00",
        )
        comment_only_post = BlueskyFeedPost(
            id="post_comment",
            uri="post_comment",
            author_display_name="Author B",
            author_handle="author-b.bsky.social",
            text="for comments",
            bookmark_count=0,
            like_count=0,
            quote_count=0,
            reply_count=0,
            repost_count=0,
            created_at="2024_01_01-12:00:00",
        )
        follow_only_post = BlueskyFeedPost(
            id="post_follow",
            uri="post_follow",
            author_display_name="Author C",
            author_handle="author-c.bsky.social",
            text="for follows",
            bookmark_count=0,
            like_count=0,
            quote_count=0,
            reply_count=0,
            repost_count=0,
            created_at="2024_01_01-12:00:00",
        )
        full_feed = [like_only_post, comment_only_post, follow_only_post]

        command_service.agent_action_feed_filter = Mock()
        command_service.agent_action_feed_filter.filter_candidates.return_value = (
            ActionCandidateFeeds(
                like_candidates=[like_only_post],
                comment_candidates=[comment_only_post],
                follow_candidates=[follow_only_post],
            )
        )
        agent.like_posts = Mock(return_value=[])
        agent.comment_posts = Mock(return_value=[])
        agent.follow_users = Mock(return_value=[])

        command_service.agent_action_rules_validator = Mock()
        command_service.agent_action_rules_validator.validate.return_value = (
            [],
            [],
            [],
        )
        command_service.agent_action_history_recorder = Mock()
        mock_repos["run_repo"].get_run.return_value = sample_run
        command_service.feed_generator.generate_feeds.return_value = {
            agent.handle: full_feed
        }
        command_service.feed_generator.generate_feeds.side_effect = None

        action_history_store = Mock()
        result = command_service._simulate_turn(
            run_id=sample_run.run_id,
            turn_number=0,
            agents=[agent],
            feed_algorithm="chronological",
            action_history_store=action_history_store,
            turn_metric_keys=DEFAULT_TURN_METRIC_KEYS,
        )

        expected_total_actions = {
            TurnAction.LIKE: 0,
            TurnAction.COMMENT: 0,
            TurnAction.FOLLOW: 0,
        }
        assert result.total_actions == expected_total_actions
        agent.like_posts.assert_called_once_with(
            [like_only_post],
            run_id=sample_run.run_id,
            turn_number=0,
        )
        agent.comment_posts.assert_called_once_with(
            [comment_only_post],
            run_id=sample_run.run_id,
            turn_number=0,
        )
        agent.follow_users.assert_called_once_with(
            [follow_only_post],
            run_id=sample_run.run_id,
            turn_number=0,
        )

    def test_simulate_turn_produces_non_zero_likes_with_real_agent_and_filter(
        self, command_service, mock_repos, sample_run, monkeypatch
    ):
        """Real agent and HistoryAwareActionFeedFilter produce non-zero likes."""
        import simulation.core.action_generators.like.algorithms.random_simple as like_mod

        monkeypatch.setattr(like_mod, "LIKE_PROBABILITY", 1.0)
        agent = SocialMediaAgent("agent1.bsky.social")
        feed_posts = [
            BlueskyFeedPost(
                id="post_1",
                uri="post_1",
                author_display_name="Author A",
                author_handle="author-a.bsky.social",
                text="content",
                bookmark_count=0,
                like_count=5,
                quote_count=0,
                reply_count=2,
                repost_count=1,
                created_at="2024_01_01-12:00:00",
            ),
            BlueskyFeedPost(
                id="post_2",
                uri="post_2",
                author_display_name="Author B",
                author_handle="author-b.bsky.social",
                text="content",
                bookmark_count=0,
                like_count=10,
                quote_count=0,
                reply_count=0,
                repost_count=0,
                created_at="2024_01_01-11:00:00",
            ),
        ]

        command_service.agent_action_feed_filter = HistoryAwareActionFeedFilter()
        command_service.feed_generator.generate_feeds.return_value = {
            agent.handle: feed_posts,
        }
        command_service.feed_generator.generate_feeds.side_effect = None
        mock_repos["run_repo"].get_run.return_value = sample_run

        action_history_store = InMemoryActionHistoryStore()
        result = command_service._simulate_turn(
            run_id=sample_run.run_id,
            turn_number=0,
            agents=[agent],
            feed_algorithm="chronological",
            action_history_store=action_history_store,
            turn_metric_keys=DEFAULT_TURN_METRIC_KEYS,
        )

        expected_min_likes = 1
        assert result.total_actions[TurnAction.LIKE] >= expected_min_likes
