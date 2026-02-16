"""Facade tests for simulation.core.engine module."""

from unittest.mock import ANY, Mock

import pytest

from db.repositories.feed_post_repository import FeedPostRepository
from db.repositories.generated_bio_repository import GeneratedBioRepository
from db.repositories.generated_feed_repository import GeneratedFeedRepository
from db.repositories.profile_repository import ProfileRepository
from db.repositories.run_repository import RunRepository
from simulation.core.command_service import SimulationCommandService
from simulation.core.engine import SimulationEngine
from simulation.core.models.agents import SocialMediaAgent
from simulation.core.models.runs import Run, RunStatus
from simulation.core.query_service import SimulationQueryService


@pytest.fixture
def deps():
    return {
        "run_repo": Mock(spec=RunRepository),
        "profile_repo": Mock(spec=ProfileRepository),
        "feed_post_repo": Mock(spec=FeedPostRepository),
        "generated_bio_repo": Mock(spec=GeneratedBioRepository),
        "generated_feed_repo": Mock(spec=GeneratedFeedRepository),
    }


@pytest.fixture
def agent_factory():
    factory = Mock()
    factory.return_value = [SocialMediaAgent("agent1.bsky.social")]
    return factory


@pytest.fixture
def query_service():
    return Mock(spec=SimulationQueryService)


@pytest.fixture
def command_service():
    return Mock(spec=SimulationCommandService)


@pytest.fixture
def engine(deps, agent_factory, query_service, command_service):
    return SimulationEngine(
        run_repo=deps["run_repo"],
        profile_repo=deps["profile_repo"],
        feed_post_repo=deps["feed_post_repo"],
        generated_bio_repo=deps["generated_bio_repo"],
        generated_feed_repo=deps["generated_feed_repo"],
        agent_factory=agent_factory,
        query_service=query_service,
        command_service=command_service,
    )


class TestSimulationEngineCompatibility:
    def test_keeps_dependency_attributes(self, engine, deps, agent_factory):
        assert engine.run_repo is deps["run_repo"]
        assert engine.profile_repo is deps["profile_repo"]
        assert engine.feed_post_repo is deps["feed_post_repo"]
        assert engine.generated_bio_repo is deps["generated_bio_repo"]
        assert engine.generated_feed_repo is deps["generated_feed_repo"]
        assert engine.agent_factory is agent_factory


class TestSimulationEngineDelegation:
    def test_delegates_query_methods(self, engine, query_service):
        engine.get_run("run_123")
        engine.list_runs()
        engine.get_turn_metadata("run_123", 0)
        engine.list_turn_metadata("run_123")
        engine.get_turn_data("run_123", 0)

        query_service.get_run.assert_called_once_with("run_123")
        query_service.list_runs.assert_called_once()
        query_service.get_turn_metadata.assert_called_once_with("run_123", 0)
        query_service.list_turn_metadata.assert_called_once_with("run_123")
        query_service.get_turn_data.assert_called_once_with("run_123", 0)

    def test_delegates_command_methods(self, engine, command_service):
        run = Run(
            run_id="run_123",
            created_at="2024_01_01-12:00:00",
            total_turns=1,
            total_agents=1,
            started_at="2024_01_01-12:00:00",
            status=RunStatus.RUNNING,
            completed_at=None,
        )
        config = type(
            "Cfg",
            (),
            {
                "feed_algorithm": "chronological",
                "num_agents": 1,
                "num_turns": 1,
            },
        )()
        agents = [SocialMediaAgent("agent1.bsky.social")]

        engine.execute_run(config)
        engine.update_run_status(run, RunStatus.FAILED)
        engine.simulate_turn(run, config, 0, agents)
        engine.simulate_turns(1, run, config, agents)
        engine.create_agents_for_run(run, config)

        command_service.execute_run.assert_called_once_with(config)
        command_service.update_run_status.assert_called_once_with(run, RunStatus.FAILED)
        command_service.simulate_turn.assert_called_once_with(
            run, config, 0, agents, action_history_store=ANY
        )
        command_service.simulate_turns.assert_called_once_with(
            1, run, config, agents, action_history_store=ANY
        )
        command_service.create_agents_for_run.assert_called_once_with(run, config)
