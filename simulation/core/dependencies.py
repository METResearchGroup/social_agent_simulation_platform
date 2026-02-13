"""Dependency injection factory for creating SimulationEngine instances."""

from collections.abc import Callable
from typing import Optional

from db.repositories.feed_post_repository import (
    FeedPostRepository,
    create_sqlite_feed_post_repository,
)
from db.repositories.generated_bio_repository import (
    GeneratedBioRepository,
    create_sqlite_generated_bio_repository,
)
from db.repositories.generated_feed_repository import (
    GeneratedFeedRepository,
    create_sqlite_generated_feed_repository,
)
from db.repositories.profile_repository import (
    ProfileRepository,
    create_sqlite_profile_repository,
)
from db.repositories.run_repository import RunRepository, create_sqlite_repository
from simulation.core.agent_action_history_recorder import AgentActionHistoryRecorder
from simulation.core.agent_action_rules_validator import AgentActionRulesValidator
from simulation.core.command_service import SimulationCommandService
from simulation.core.engine import SimulationEngine
from simulation.core.exceptions import InsufficientAgentsError
from simulation.core.models.agents import SocialMediaAgent
from simulation.core.query_service import SimulationQueryService


def create_default_agent_factory() -> Callable[[int], list[SocialMediaAgent]]:
    """Create the default agent factory that wraps create_initial_agents().

    This factory function creates a callable that can be used to generate
    agents for a simulation run. It wraps the existing create_initial_agents()
    function and applies the requested limit.

    Returns:
        A callable that takes num_agents (int) and returns a list of agents.

    Example:
        >>> factory = create_default_agent_factory()
        >>> agents = factory(10)  # Returns up to 10 agents
    """

    def agent_factory(num_agents: int) -> list[SocialMediaAgent]:
        """Create agents for a simulation run.

        Args:
            num_agents: Number of agents to create (will be limited to available).

        Returns:
            A list of agents, limited to num_agents.

        Raises:
            InsufficientAgentsError: If no agents are available or fewer than
                requested are available.
        """
        from ai.create_initial_agents import create_initial_agents

        # Create all available agents
        all_agents = create_initial_agents()

        # Apply limit
        agents = all_agents[:num_agents]

        # Validate agent count
        if len(agents) < num_agents or len(agents) == 0:
            raise InsufficientAgentsError(
                requested=num_agents,
                available=len(all_agents),
            )

        return agents

    return agent_factory


def create_engine(
    *,
    run_repo: Optional[RunRepository] = None,
    profile_repo: Optional[ProfileRepository] = None,
    feed_post_repo: Optional[FeedPostRepository] = None,
    generated_bio_repo: Optional[GeneratedBioRepository] = None,
    generated_feed_repo: Optional[GeneratedFeedRepository] = None,
    agent_factory: Optional[Callable[[int], list[SocialMediaAgent]]] = None,
) -> SimulationEngine:
    """Create a SimulationEngine with injected dependencies.

    This factory function creates a SimulationEngine instance with all required
    dependencies. If a dependency is not provided, it defaults to creating a
    SQLite repository or the default agent factory.

    Args:
        run_repo: Optional. Run repository. Defaults to SQLite implementation.
        profile_repo: Optional. Profile repository. Defaults to SQLite implementation.
        feed_post_repo: Optional. Feed post repository. Defaults to SQLite implementation.
        generated_bio_repo: Optional. Generated bio repository. Defaults to SQLite implementation.
        generated_feed_repo: Optional. Generated feed repository. Defaults to SQLite implementation.
        agent_factory: Optional. Agent factory function. Defaults to create_default_agent_factory().

    Returns:
        A configured SimulationEngine instance.

    Example:
        >>> # Use all defaults
        >>> engine = create_engine()
        >>>
        >>> # Override specific dependencies
        >>> engine = create_engine(
        ...     run_repo=my_custom_repo,
        ...     agent_factory=my_custom_factory,
        ... )
    """
    # Create default repositories if not provided
    if run_repo is None:
        run_repo = create_sqlite_repository()
    if profile_repo is None:
        profile_repo = create_sqlite_profile_repository()
    if feed_post_repo is None:
        feed_post_repo = create_sqlite_feed_post_repository()
    if generated_bio_repo is None:
        generated_bio_repo = create_sqlite_generated_bio_repository()
    if generated_feed_repo is None:
        generated_feed_repo = create_sqlite_generated_feed_repository()

    # Create default agent factory if not provided
    if agent_factory is None:
        agent_factory = create_default_agent_factory()

    query_service = create_query_service(
        run_repo=run_repo,
        feed_post_repo=feed_post_repo,
        generated_feed_repo=generated_feed_repo,
    )
    command_service = create_command_service(
        run_repo=run_repo,
        profile_repo=profile_repo,
        feed_post_repo=feed_post_repo,
        generated_bio_repo=generated_bio_repo,
        generated_feed_repo=generated_feed_repo,
        agent_factory=agent_factory,
    )

    return SimulationEngine(
        run_repo=run_repo,
        profile_repo=profile_repo,
        feed_post_repo=feed_post_repo,
        generated_bio_repo=generated_bio_repo,
        generated_feed_repo=generated_feed_repo,
        agent_factory=agent_factory,
        query_service=query_service,
        command_service=command_service,
    )


def create_query_service(
    *,
    run_repo: RunRepository,
    feed_post_repo: FeedPostRepository,
    generated_feed_repo: GeneratedFeedRepository,
) -> SimulationQueryService:
    """Create query-side service with read dependencies."""
    return SimulationQueryService(
        run_repo=run_repo,
        feed_post_repo=feed_post_repo,
        generated_feed_repo=generated_feed_repo,
    )


def create_command_service(
    *,
    run_repo: RunRepository,
    profile_repo: ProfileRepository,
    feed_post_repo: FeedPostRepository,
    generated_bio_repo: GeneratedBioRepository,
    generated_feed_repo: GeneratedFeedRepository,
    agent_factory: Callable[[int], list[SocialMediaAgent]],
    agent_action_rules_validator: Optional[AgentActionRulesValidator] = None,
    agent_action_history_recorder: Optional[AgentActionHistoryRecorder] = None,
) -> SimulationCommandService:
    """Create command-side service with execution dependencies."""
    return SimulationCommandService(
        run_repo=run_repo,
        profile_repo=profile_repo,
        feed_post_repo=feed_post_repo,
        generated_bio_repo=generated_bio_repo,
        generated_feed_repo=generated_feed_repo,
        agent_factory=agent_factory,
        agent_action_rules_validator=agent_action_rules_validator
        or AgentActionRulesValidator(),
        agent_action_history_recorder=agent_action_history_recorder
        or AgentActionHistoryRecorder(),
    )
