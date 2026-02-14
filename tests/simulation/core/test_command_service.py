"""Tests for simulation.core.command_service module."""

from unittest.mock import Mock, patch

import pytest

from db.exceptions import RunStatusUpdateError
from db.repositories.feed_post_repository import FeedPostRepository
from db.repositories.generated_bio_repository import GeneratedBioRepository
from db.repositories.generated_feed_repository import GeneratedFeedRepository
from db.repositories.profile_repository import ProfileRepository
from db.repositories.run_repository import RunRepository
from simulation.core.command_service import SimulationCommandService
from simulation.core.models.actions import Comment, Follow, Like, TurnAction
from simulation.core.models.agents import SocialMediaAgent
from simulation.core.models.generated.base import GenerationMetadata
from simulation.core.models.generated.comment import GeneratedComment
from simulation.core.models.generated.follow import GeneratedFollow
from simulation.core.models.generated.like import GeneratedLike
from simulation.core.models.posts import BlueskyFeedPost
from simulation.core.models.runs import Run, RunStatus
from simulation.core.models.turns import TurnResult


@pytest.fixture
def mock_repos():
    return {
        "run_repo": Mock(spec=RunRepository),
        "profile_repo": Mock(spec=ProfileRepository),
        "feed_post_repo": Mock(spec=FeedPostRepository),
        "generated_bio_repo": Mock(spec=GeneratedBioRepository),
        "generated_feed_repo": Mock(spec=GeneratedFeedRepository),
    }


@pytest.fixture
def mock_agent_factory():
    factory = Mock()
    factory.side_effect = lambda num_agents: [
        SocialMediaAgent(f"agent{i}.bsky.social") for i in range(num_agents)
    ]
    return factory


@pytest.fixture
def command_service(mock_repos, mock_agent_factory):
    action_history_store_factory = Mock(return_value=Mock())
    return SimulationCommandService(
        run_repo=mock_repos["run_repo"],
        profile_repo=mock_repos["profile_repo"],
        feed_post_repo=mock_repos["feed_post_repo"],
        generated_bio_repo=mock_repos["generated_bio_repo"],
        generated_feed_repo=mock_repos["generated_feed_repo"],
        agent_factory=mock_agent_factory,
        action_history_store_factory=action_history_store_factory,
    )


@pytest.fixture
def sample_run():
    return Run(
        run_id="run_123",
        created_at="2024_01_01-12:00:00",
        total_turns=2,
        total_agents=2,
        started_at="2024_01_01-12:00:00",
        status=RunStatus.RUNNING,
        completed_at=None,
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
            },
        )()

    def test_success_path(self, command_service, mock_repos, sample_run, mock_agent_factory):
        mock_repos["run_repo"].create_run.return_value = sample_run
        mock_repos["run_repo"].update_run_status.side_effect = [None, None]
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
        calls = mock_repos["run_repo"].update_run_status.call_args_list
        assert calls[0][0] == (sample_run.run_id, RunStatus.RUNNING)
        assert calls[1][0] == (sample_run.run_id, RunStatus.COMPLETED)

    def test_agent_creation_failure_marks_failed(
        self, command_service, mock_repos, sample_run, mock_agent_factory
    ):
        mock_repos["run_repo"].create_run.return_value = sample_run
        mock_repos["run_repo"].update_run_status.return_value = None
        mock_agent_factory.side_effect = RuntimeError("agent failure")

        with pytest.raises(RuntimeError):
            command_service.execute_run(self._make_config(turns=1))

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
            with pytest.raises(RuntimeError, match="Failed to complete turn"):
                command_service.execute_run(self._make_config(turns=1))

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
                    ai_reason="reason",
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
                        created_at="2024_01_01-12:00:00",
                    ),
                    ai_reason="reason",
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
                    ai_reason="reason",
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

        with patch(
            "feeds.feed_generator.generate_feeds",
            return_value={agent.handle: [feed_post]},
        ):
            result = command_service._simulate_turn(
                run_id=sample_run.run_id,
                turn_number=0,
                agents=[agent],
                feed_algorithm="chronological",
            )

        assert result.total_actions[TurnAction.LIKE] == 1
        assert result.total_actions[TurnAction.COMMENT] == 1
        assert result.total_actions[TurnAction.FOLLOW] == 1
        command_service.agent_action_rules_validator.validate.assert_called_once()
        command_service.agent_action_history_recorder.record.assert_called_once()
