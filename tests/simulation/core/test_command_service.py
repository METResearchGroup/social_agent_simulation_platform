"""Tests for simulation.core.command_service module."""

from unittest.mock import Mock, patch

import pytest

from db.services.simulation_persistence_service import SimulationPersistenceService
from feeds.interfaces import FeedGenerator
from simulation.core.action_history import InMemoryActionHistoryStore
from simulation.core.action_policy import (
    ActionCandidateFeeds,
    AgentActionRulesValidator,
    HistoryAwareActionFeedFilter,
)
from simulation.core.command_service import SimulationCommandService
from simulation.core.exceptions import RunStatusUpdateError, SimulationRunFailure
from simulation.core.metrics.collector import MetricsCollector
from simulation.core.metrics.defaults import DEFAULT_TURN_METRIC_KEYS
from simulation.core.models.actions import TurnAction
from simulation.core.models.agent_seed_actions import (
    AgentSeedComment,
    AgentSeedFollow,
    AgentSeedLike,
)
from simulation.core.models.agents import SocialMediaAgent
from simulation.core.models.runs import RunStatus
from tests.factories import (
    AgentFactory,
    CommentFactory,
    FollowFactory,
    GeneratedCommentFactory,
    GeneratedFollowFactory,
    GeneratedLikeFactory,
    GenerationMetadataFactory,
    LikeFactory,
    PostFactory,
    RunConfigFactory,
    TurnResultFactory,
)


@pytest.fixture
def mock_agent_factory():
    factory = Mock()
    factory.side_effect = lambda num_agents: [
        AgentFactory.create(handle=f"agent{i}.bsky.social") for i in range(num_agents)
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
        agent_seed_like_repo=mock_repos["agent_seed_like_repo"],
        agent_seed_comment_repo=mock_repos["agent_seed_comment_repo"],
        agent_seed_follow_repo=mock_repos["agent_seed_follow_repo"],
        agent_factory=mock_agent_factory,
        action_history_store_factory=action_history_store_factory,
        feed_generator=mock_feed_generator,
        agent_action_rules_validator=agent_action_rules_validator,
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
            AgentFactory.create(handle="agent1.bsky.social"),
            AgentFactory.create(handle="agent2.bsky.social"),
        ]

        with patch(
            "simulation.core.command_service.SimulationCommandService._simulate_turn"
        ) as mock_sim_turn:
            mock_sim_turn.side_effect = [
                TurnResultFactory.create(
                    turn_number=0, total_actions={}, execution_time_ms=10
                ),
                TurnResultFactory.create(
                    turn_number=1, total_actions={}, execution_time_ms=12
                ),
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

    def test_seeds_action_history_from_agent_seed_repos(
        self, mock_repos, mock_agent_factory
    ):
        """execute_run seeds ActionHistoryStore from persisted agent seed actions."""
        # Arrange a real history store so we can assert seeded state.
        history = InMemoryActionHistoryStore()
        agent_handle = "@seed.agent.bsky.social"
        agent = SocialMediaAgent(agent_handle)

        seed_like_repo = Mock()
        seed_like_repo.read_agent_seed_likes_by_agent_handles.return_value = [
            AgentSeedLike(
                seed_like_id="sl1",
                agent_handle=agent_handle,
                post_uri="at://did:plc:post1",
                created_at="2026-02-25T00:00:00Z",
            )
        ]
        seed_comment_repo = Mock()
        seed_comment_repo.read_agent_seed_comments_by_agent_handles.return_value = [
            AgentSeedComment(
                seed_comment_id="sc1",
                agent_handle=agent_handle,
                post_uri="at://did:plc:post2",
                text="hello",
                created_at="2026-02-25T00:00:00Z",
            )
        ]
        seed_follow_repo = Mock()
        seed_follow_repo.read_agent_seed_follows_by_agent_handles.return_value = [
            AgentSeedFollow(
                seed_follow_id="sf1",
                agent_handle=agent_handle,
                user_id="@other.bsky.social",
                created_at="2026-02-25T00:00:00Z",
            )
        ]

        service = SimulationCommandService(
            run_repo=mock_repos["run_repo"],
            metrics_repo=mock_repos["metrics_repo"],
            metrics_collector=Mock(spec=MetricsCollector),
            simulation_persistence=Mock(spec=SimulationPersistenceService),
            profile_repo=mock_repos["profile_repo"],
            feed_post_repo=mock_repos["feed_post_repo"],
            generated_bio_repo=mock_repos["generated_bio_repo"],
            generated_feed_repo=mock_repos["generated_feed_repo"],
            agent_seed_like_repo=seed_like_repo,
            agent_seed_comment_repo=seed_comment_repo,
            agent_seed_follow_repo=seed_follow_repo,
            agent_factory=mock_agent_factory,
            action_history_store_factory=Mock(return_value=history),
            feed_generator=Mock(spec=FeedGenerator),
            agent_action_rules_validator=Mock(spec=AgentActionRulesValidator),
            agent_action_feed_filter=Mock(spec=HistoryAwareActionFeedFilter),
        )

        # Act: call the seeding hook directly (execute_run uses this before turns).
        service._seed_action_history_store_from_agent_seeds(
            run_id="run_1", agents=[agent], action_history_store=history
        )

        # Assert
        assert history.has_liked("run_1", agent_handle, "at://did:plc:post1")
        assert history.has_commented("run_1", agent_handle, "at://did:plc:post2")
        assert history.has_followed("run_1", agent_handle, "@other.bsky.social")

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
        mock_agent_factory.return_value = [
            AgentFactory.create(handle="agent1.bsky.social")
        ]

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
        agent = AgentFactory.create(handle="agent1.bsky.social")
        feed_post = PostFactory.create(
            post_id="post_1",
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

        metadata = GenerationMetadataFactory.create(created_at="2024_01_01-12:00:00")
        mock_generate_likes = Mock(
            return_value=[
                GeneratedLikeFactory.create(
                    like=LikeFactory.create(
                        like_id="like_1",
                        agent_id=agent.handle,
                        post_id="post_1",
                        created_at="2024_01_01-12:00:00",
                    ),
                    explanation="reason",
                    metadata=metadata,
                ),
            ]
        )
        mock_generate_comments = Mock(
            return_value=[
                GeneratedCommentFactory.create(
                    comment=CommentFactory.create(
                        comment_id="comment_1",
                        agent_id=agent.handle,
                        post_id="post_1",
                        text="nice post",
                        created_at="2024_01_01-12:00:00",
                    ),
                    explanation="reason",
                    metadata=metadata,
                ),
            ]
        )
        mock_generate_follows = Mock(
            return_value=[
                GeneratedFollowFactory.create(
                    follow=FollowFactory.create(
                        follow_id="follow_1",
                        agent_id=agent.handle,
                        user_id="user_1",
                        created_at="2024_01_01-12:00:00",
                    ),
                    explanation="reason",
                    metadata=metadata,
                ),
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

        with (
            patch(
                "simulation.core.command_service.generate_likes", mock_generate_likes
            ),
            patch(
                "simulation.core.command_service.generate_comments",
                mock_generate_comments,
            ),
            patch(
                "simulation.core.command_service.generate_follows",
                mock_generate_follows,
            ),
        ):
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
        action_history_store.record_like.assert_called_once_with(
            sample_run.run_id,
            agent.handle,
            "post_1",
        )
        action_history_store.record_comment.assert_called_once_with(
            sample_run.run_id,
            agent.handle,
            "post_1",
        )
        action_history_store.record_follow.assert_called_once_with(
            sample_run.run_id,
            agent.handle,
            "user_1",
        )

    def test_simulate_turn_uses_action_specific_filtered_candidates(
        self, command_service, mock_repos, sample_run
    ):
        agent = AgentFactory.create(handle="agent1.bsky.social")
        like_only_post = PostFactory.create(
            post_id="post_like",
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
        comment_only_post = PostFactory.create(
            post_id="post_comment",
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
        follow_only_post = PostFactory.create(
            post_id="post_follow",
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
        mock_generate_likes = Mock(return_value=[])
        mock_generate_comments = Mock(return_value=[])
        mock_generate_follows = Mock(return_value=[])

        command_service.agent_action_rules_validator = Mock()
        command_service.agent_action_rules_validator.validate.return_value = (
            [],
            [],
            [],
        )
        mock_repos["run_repo"].get_run.return_value = sample_run
        command_service.feed_generator.generate_feeds.return_value = {
            agent.handle: full_feed
        }
        command_service.feed_generator.generate_feeds.side_effect = None

        with (
            patch(
                "simulation.core.command_service.generate_likes", mock_generate_likes
            ),
            patch(
                "simulation.core.command_service.generate_comments",
                mock_generate_comments,
            ),
            patch(
                "simulation.core.command_service.generate_follows",
                mock_generate_follows,
            ),
        ):
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
        mock_generate_likes.assert_called_once_with(
            [like_only_post],
            run_id=sample_run.run_id,
            turn_number=0,
            agent_handle=agent.handle,
        )
        mock_generate_comments.assert_called_once_with(
            [comment_only_post],
            run_id=sample_run.run_id,
            turn_number=0,
            agent_handle=agent.handle,
        )
        mock_generate_follows.assert_called_once_with(
            [follow_only_post],
            run_id=sample_run.run_id,
            turn_number=0,
            agent_handle=agent.handle,
        )

    def test_simulate_turn_produces_non_zero_likes_with_real_agent_and_filter(
        self, command_service, mock_repos, sample_run, monkeypatch
    ):
        """Real agent and HistoryAwareActionFeedFilter produce non-zero likes."""
        import simulation.core.action_generators.like.algorithms.random_simple as like_mod

        monkeypatch.setattr(like_mod, "LIKE_PROBABILITY", 1.0)
        agent = AgentFactory.create(handle="agent1.bsky.social")
        feed_posts = [
            PostFactory.create(
                post_id="post_1",
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
            PostFactory.create(
                post_id="post_2",
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


class TestSimulationCommandServiceActionPersistence:
    """Tests that simulate_turn persists actions to DB when using real persistence."""

    def test_simulate_turn_persists_likes_comments_follows_to_db(
        self,
        run_repo,
        metrics_repo,
        like_repo,
        comment_repo,
        follow_repo,
    ):
        """Execute one turn with real persistence; assert likes/comments/follows are persisted."""
        from db.adapters.sqlite.sqlite import SqliteTransactionProvider
        from db.services.simulation_persistence_service import (
            create_simulation_persistence_service,
        )
        from simulation.core.action_history import (
            create_default_action_history_store_factory,
        )

        transaction_provider = SqliteTransactionProvider()
        simulation_persistence = create_simulation_persistence_service(
            run_repo=run_repo,
            metrics_repo=metrics_repo,
            transaction_provider=transaction_provider,
            like_repo=like_repo,
            comment_repo=comment_repo,
            follow_repo=follow_repo,
        )
        run = run_repo.create_run(
            RunConfigFactory.create(
                num_agents=1, num_turns=1, feed_algorithm="chronological"
            )
        )
        run_id = run.run_id
        run_repo.update_run_status(run_id, RunStatus.RUNNING)

        agent = AgentFactory.create(handle="agent1.bsky.social")
        metadata = GenerationMetadataFactory.create(
            model_used=None,
            generation_metadata=None,
            created_at="2026-02-24T12:00:00Z",
        )
        mock_generate_likes = Mock(
            return_value=[
                GeneratedLikeFactory.create(
                    like=LikeFactory.create(
                        like_id="like_1",
                        agent_id=agent.handle,
                        post_id="at://did:plc:post1",
                        created_at="2026-02-24T12:00:00Z",
                    ),
                    explanation="Great",
                    metadata=metadata,
                ),
            ]
        )
        mock_generate_comments = Mock(
            return_value=[
                GeneratedCommentFactory.create(
                    comment=CommentFactory.create(
                        comment_id="comment_1",
                        agent_id=agent.handle,
                        post_id="at://did:plc:post1",
                        text="Nice!",
                        created_at="2026-02-24T12:00:00Z",
                    ),
                    explanation="Relevant",
                    metadata=metadata,
                ),
            ]
        )
        mock_generate_follows = Mock(
            return_value=[
                GeneratedFollowFactory.create(
                    follow=FollowFactory.create(
                        follow_id="follow_1",
                        agent_id=agent.handle,
                        user_id="user2.bsky.social",
                        created_at="2026-02-24T12:00:00Z",
                    ),
                    explanation="Interesting",
                    metadata=metadata,
                ),
            ]
        )

        feed_post = PostFactory.create(
            post_id="post_1",
            uri="at://did:plc:post1",
            author_display_name="Author",
            author_handle="author.bsky.social",
            text="Hello",
            bookmark_count=0,
            like_count=0,
            quote_count=0,
            reply_count=0,
            repost_count=0,
            created_at="2026-02-24T12:00:00",
        )
        feed_generator = Mock(spec=FeedGenerator)
        feed_generator.generate_feeds.side_effect = lambda **kwargs: {
            a.handle: [feed_post] for a in kwargs["agents"]
        }
        action_history_store_factory = create_default_action_history_store_factory()
        action_history_store = action_history_store_factory()
        agent_action_feed_filter = HistoryAwareActionFeedFilter()
        agent_action_rules_validator = AgentActionRulesValidator()
        metrics_collector = Mock(spec=MetricsCollector)
        metrics_collector.collect_turn_metrics.return_value = {}

        command_service = SimulationCommandService(
            run_repo=run_repo,
            metrics_repo=metrics_repo,
            metrics_collector=metrics_collector,
            simulation_persistence=simulation_persistence,
            profile_repo=Mock(),
            feed_post_repo=Mock(),
            generated_bio_repo=Mock(),
            generated_feed_repo=Mock(),
            agent_seed_like_repo=Mock(),
            agent_seed_comment_repo=Mock(),
            agent_seed_follow_repo=Mock(),
            agent_factory=lambda n: [agent],
            action_history_store_factory=lambda: action_history_store,
            feed_generator=feed_generator,
            agent_action_rules_validator=agent_action_rules_validator,
            agent_action_feed_filter=agent_action_feed_filter,
        )

        with (
            patch(
                "simulation.core.command_service.generate_likes", mock_generate_likes
            ),
            patch(
                "simulation.core.command_service.generate_comments",
                mock_generate_comments,
            ),
            patch(
                "simulation.core.command_service.generate_follows",
                mock_generate_follows,
            ),
        ):
            command_service._simulate_turn(
                run_id=run_id,
                turn_number=0,
                agents=[agent],
                feed_algorithm="chronological",
                action_history_store=action_history_store,
                turn_metric_keys=DEFAULT_TURN_METRIC_KEYS,
            )

        persisted_likes = like_repo.read_likes_by_run_turn(run_id, 0)
        persisted_comments = comment_repo.read_comments_by_run_turn(run_id, 0)
        persisted_follows = follow_repo.read_follows_by_run_turn(run_id, 0)

        assert len(persisted_likes) == 1
        assert persisted_likes[0].like_id == "like_1"
        assert persisted_likes[0].agent_handle == "agent1.bsky.social"
        assert persisted_likes[0].post_id == "at://did:plc:post1"

        assert len(persisted_comments) == 1
        assert persisted_comments[0].comment_id == "comment_1"
        assert persisted_comments[0].agent_handle == "agent1.bsky.social"
        assert persisted_comments[0].text == "Nice!"

        assert len(persisted_follows) == 1
        assert persisted_follows[0].follow_id == "follow_1"
        assert persisted_follows[0].agent_handle == "agent1.bsky.social"
        assert persisted_follows[0].user_id == "user2.bsky.social"
