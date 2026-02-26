"""Factory for creating the default agent factory."""

from collections.abc import Callable

from db.repositories.interfaces import (
    FeedPostRepository,
    GeneratedBioRepository,
    ProfileRepository,
)
from simulation.core.models.agents import SocialMediaAgent
from simulation.core.utils.validators import (
    validate_duplicate_agent_handles,
    validate_insufficient_agents,
)


def create_default_agent_factory(
    *,
    profile_repo: ProfileRepository,
    feed_post_repo: FeedPostRepository,
    generated_bio_repo: GeneratedBioRepository,
) -> Callable[[int], list[SocialMediaAgent]]:
    """Create the default agent factory that wraps create_initial_agents().

    This factory function creates a callable that can be used to generate
    agents for a simulation run. It wraps the existing create_initial_agents()
    function and applies the requested limit.

    Returns:
        A callable that takes num_agents (int) and returns a list of agents.

    Example:
        >>> factory = create_default_agent_factory(
        ...     profile_repo=profile_repo,
        ...     feed_post_repo=feed_post_repo,
        ...     generated_bio_repo=generated_bio_repo,
        ... )
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
        all_agents = create_initial_agents(
            profile_repo=profile_repo,
            feed_post_repo=feed_post_repo,
            generated_bio_repo=generated_bio_repo,
        )

        # Apply limit
        agents = all_agents[:num_agents]

        # Validate agents
        validate_insufficient_agents(agents=agents, requested_agents=num_agents)
        validate_duplicate_agent_handles(agents=agents)

        return agents

    return agent_factory
