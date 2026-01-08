"""Tests for simulation.core.dependencies module."""

from unittest.mock import Mock, patch

import pytest

from db.repositories.feed_post_repository import FeedPostRepository
from db.repositories.generated_bio_repository import GeneratedBioRepository
from db.repositories.generated_feed_repository import GeneratedFeedRepository
from db.repositories.profile_repository import ProfileRepository
from db.repositories.run_repository import RunRepository
from simulation.core.dependencies import create_default_agent_factory, create_engine
from simulation.core.engine import SimulationEngine
from simulation.core.exceptions import InsufficientAgentsError
from simulation.core.models.agents import SocialMediaAgent


class TestCreateEngine:
    """Tests for create_engine function."""

    def test_creates_engine_with_default_dependencies(self):
        """Test that create_engine() creates an engine with all default dependencies."""
        # Act
        engine = create_engine()

        # Assert
        assert isinstance(engine, SimulationEngine)
        assert engine.run_repo is not None
        assert engine.profile_repo is not None
        assert engine.feed_post_repo is not None
        assert engine.generated_bio_repo is not None
        assert engine.generated_feed_repo is not None
        assert engine.agent_factory is not None

    def test_creates_engine_with_provided_repositories(self):
        """Test that create_engine() uses provided repositories when specified."""
        # Arrange
        mock_run_repo = Mock(spec=RunRepository)
        mock_profile_repo = Mock(spec=ProfileRepository)
        mock_feed_post_repo = Mock(spec=FeedPostRepository)
        mock_generated_bio_repo = Mock(spec=GeneratedBioRepository)
        mock_generated_feed_repo = Mock(spec=GeneratedFeedRepository)
        mock_agent_factory = Mock(return_value=[])

        # Act
        engine = create_engine(
            run_repo=mock_run_repo,
            profile_repo=mock_profile_repo,
            feed_post_repo=mock_feed_post_repo,
            generated_bio_repo=mock_generated_bio_repo,
            generated_feed_repo=mock_generated_feed_repo,
            agent_factory=mock_agent_factory,
        )

        # Assert
        assert isinstance(engine, SimulationEngine)
        assert engine.run_repo is mock_run_repo
        assert engine.profile_repo is mock_profile_repo
        assert engine.feed_post_repo is mock_feed_post_repo
        assert engine.generated_bio_repo is mock_generated_bio_repo
        assert engine.generated_feed_repo is mock_generated_feed_repo
        assert engine.agent_factory is mock_agent_factory

    def test_creates_engine_with_mix_of_defaults_and_provided(self):
        """Test that create_engine() creates defaults for None values and uses provided ones."""
        # Arrange
        mock_run_repo = Mock(spec=RunRepository)
        mock_agent_factory = Mock(return_value=[])

        # Act
        engine = create_engine(
            run_repo=mock_run_repo,
            agent_factory=mock_agent_factory,
        )

        # Assert
        assert isinstance(engine, SimulationEngine)
        assert engine.run_repo is mock_run_repo
        assert engine.agent_factory is mock_agent_factory
        # Other repos should be defaults (not None, actual instances)
        assert engine.profile_repo is not None
        assert engine.feed_post_repo is not None
        assert engine.generated_bio_repo is not None
        assert engine.generated_feed_repo is not None

    def test_creates_engine_with_all_repository_types(self):
        """Test that create_engine() creates repositories of correct types."""
        # Act
        engine = create_engine()

        # Assert
        assert isinstance(engine.run_repo, RunRepository)
        assert isinstance(engine.profile_repo, ProfileRepository)
        assert isinstance(engine.feed_post_repo, FeedPostRepository)
        assert isinstance(engine.generated_bio_repo, GeneratedBioRepository)
        assert isinstance(engine.generated_feed_repo, GeneratedFeedRepository)
        assert callable(engine.agent_factory)


class TestCreateDefaultAgentFactory:
    """Tests for create_default_agent_factory function."""

    def test_returns_callable(self):
        """Test that create_default_agent_factory() returns a callable."""
        # Act
        factory = create_default_agent_factory()

        # Assert
        assert callable(factory)

    @patch("ai.create_initial_agents.create_initial_agents")
    def test_returns_correct_number_of_agents(self, mock_create_agents):
        """Test that the factory returns the correct number of agents."""
        # Arrange
        # Create 10 mock agents
        mock_agents = [SocialMediaAgent(f"agent{i}.bsky.social") for i in range(10)]
        mock_create_agents.return_value = mock_agents
        factory = create_default_agent_factory()

        # Act
        result = factory(5)  # Request 5 agents

        # Assert
        assert len(result) == 5
        assert all(isinstance(agent, SocialMediaAgent) for agent in result)
        mock_create_agents.assert_called_once()

    @patch("ai.create_initial_agents.create_initial_agents")
    def test_handles_limit_correctly(self, mock_create_agents):
        """Test that the factory correctly limits the number of agents returned."""
        # Arrange
        # Create 10 mock agents
        mock_agents = [SocialMediaAgent(f"agent{i}.bsky.social") for i in range(10)]
        mock_create_agents.return_value = mock_agents
        factory = create_default_agent_factory()

        # Act
        result = factory(3)  # Request 3 agents

        # Assert
        assert len(result) == 3
        # Should be first 3 agents
        assert result[0].handle == "agent0.bsky.social"
        assert result[1].handle == "agent1.bsky.social"
        assert result[2].handle == "agent2.bsky.social"

    @patch("ai.create_initial_agents.create_initial_agents")
    def test_raises_insufficient_agents_error_when_no_agents(self, mock_create_agents):
        """Test that the factory raises InsufficientAgentsError when no agents are available."""
        # Arrange
        mock_create_agents.return_value = []  # No agents available
        factory = create_default_agent_factory()

        # Act & Assert
        with pytest.raises(InsufficientAgentsError) as exc_info:
            factory(5)

        assert exc_info.value.requested == 5
        assert exc_info.value.available == 0

    @patch("ai.create_initial_agents.create_initial_agents")
    def test_raises_insufficient_agents_error_when_fewer_than_requested(
        self, mock_create_agents
    ):
        """Test that the factory raises InsufficientAgentsError when fewer agents than requested."""
        # Arrange
        # Only 3 agents available
        mock_agents = [SocialMediaAgent(f"agent{i}.bsky.social") for i in range(3)]
        mock_create_agents.return_value = mock_agents
        factory = create_default_agent_factory()

        # Act & Assert
        with pytest.raises(InsufficientAgentsError) as exc_info:
            factory(10)  # Request 10, but only 3 available

        assert exc_info.value.requested == 10
        assert exc_info.value.available == 3

    @patch("ai.create_initial_agents.create_initial_agents")
    def test_returns_all_agents_when_requested_exactly_available(
        self, mock_create_agents
    ):
        """Test that the factory returns all agents when requested count equals available."""
        # Arrange
        # Only 3 agents available
        mock_agents = [SocialMediaAgent(f"agent{i}.bsky.social") for i in range(3)]
        mock_create_agents.return_value = mock_agents
        factory = create_default_agent_factory()

        # Act
        result = factory(3)  # Request exactly 3, which matches available

        # Assert
        assert len(result) == 3
        assert all(isinstance(agent, SocialMediaAgent) for agent in result)

    @patch("ai.create_initial_agents.create_initial_agents")
    def test_calls_create_initial_agents_once_per_call(self, mock_create_agents):
        """Test that the factory calls create_initial_agents once per factory call."""
        # Arrange
        mock_agents = [SocialMediaAgent(f"agent{i}.bsky.social") for i in range(10)]
        mock_create_agents.return_value = mock_agents
        factory = create_default_agent_factory()

        # Act
        factory(5)
        factory(3)

        # Assert
        assert mock_create_agents.call_count == 2
