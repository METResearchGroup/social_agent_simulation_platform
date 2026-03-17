"""Factory helpers for constructing runtime simulation agents."""

from collections.abc import Callable

from db.repositories.interfaces import (
    AgentBioRepository,
    AgentRepository,
    FeedPostRepository,
    UserAgentProfileMetadataRepository,
)
from simulation.core.models.agents import SimulationAgent
from simulation.core.models.posts import Post
from simulation.core.seed_state import hydrate_seed_state
from simulation.core.utils.validators import (
    validate_duplicate_agent_handles,
    validate_insufficient_agents,
)


def create_default_agent_factory(
    *,
    agent_repo: AgentRepository,
    agent_bio_repo: AgentBioRepository,
    user_agent_profile_metadata_repo: UserAgentProfileMetadataRepository,
    feed_post_repo: FeedPostRepository,
) -> Callable[[int], list[SimulationAgent]]:
    """Create the default agent factory that hydrates seed-state agents.

    This factory function creates a callable that can be used to generate
    agents for a simulation run. It hydrates the current seed-state catalog and
    applies the requested limit.

    Returns:
        A callable that takes num_agents (int) and returns a list of agents.

    Example:
        >>> factory = create_default_agent_factory(
        ...     agent_repo=agent_repo,
        ...     agent_bio_repo=agent_bio_repo,
        ...     user_agent_profile_metadata_repo=user_agent_profile_metadata_repo,
        ...     feed_post_repo=feed_post_repo,
        ... )
        >>> agents = factory(10)  # Returns up to 10 agents
    """

    def agent_factory(num_agents: int) -> list[SimulationAgent]:
        """Create agents for a simulation run.

        Args:
            num_agents: Number of agents to create (will be limited to available).

        Returns:
            A list of agents, limited to num_agents.

        Raises:
            InsufficientAgentsError: If no agents are available or fewer than
                requested are available.
        """
        # Create all available agents
        all_agents = _create_simulation_agents_from_seed_state(
            agent_repo=agent_repo,
            agent_bio_repo=agent_bio_repo,
            user_agent_profile_metadata_repo=user_agent_profile_metadata_repo,
            feed_post_repo=feed_post_repo,
        )

        # Apply limit
        agents = all_agents[:num_agents]

        # Validate agents
        validate_insufficient_agents(agents=agents, requested_agents=num_agents)
        validate_duplicate_agent_handles(agents=agents)

        return agents

    return agent_factory


def _create_simulation_agents_from_seed_state(
    *,
    agent_repo: AgentRepository,
    agent_bio_repo: AgentBioRepository,
    user_agent_profile_metadata_repo: UserAgentProfileMetadataRepository,
    feed_post_repo: FeedPostRepository,
) -> list[SimulationAgent]:
    """Hydrate runtime simulation agents from the current seed-state catalog."""
    seed_state = hydrate_seed_state(
        agent_repo=agent_repo,
        agent_bio_repo=agent_bio_repo,
        user_agent_profile_metadata_repo=user_agent_profile_metadata_repo,
    )
    agent_records = seed_state.ordered_agents
    latest_bios = seed_state.latest_bios
    metadata_by_agent_id = seed_state.metadata_by_agent_id
    feed_posts: list[Post] = feed_post_repo.list_all_feed_posts()

    handle_to_feed_posts: dict[str, list[Post]] = {}
    for post in feed_posts:
        handle_to_feed_posts.setdefault(post.author_handle, []).append(post)

    agents: list[SimulationAgent] = []

    # Build agents from seed state so later run snapshots can FK back to
    # the selected `agent.agent_id` rows.
    for agent_record in agent_records:
        latest_bio = latest_bios.get(agent_record.agent_id)
        if latest_bio is None:
            raise ValueError(
                f"Missing latest agent bio for seed agent {agent_record.agent_id}"
            )

        metadata = metadata_by_agent_id.get(agent_record.agent_id)
        if metadata is None:
            raise ValueError(
                "Missing user agent profile metadata for seed agent "
                f"{agent_record.agent_id}"
            )

        agent = SimulationAgent(
            agent_record.handle,
            agent_id=agent_record.agent_id,
            display_name=agent_record.display_name,
        )
        agent.bio = latest_bio.persona_bio
        agent.followers = metadata.followers_count
        agent.following = metadata.follows_count
        agent.posts_count = metadata.posts_count
        agent.posts = handle_to_feed_posts.get(agent_record.handle, [])
        agent.likes = []
        agent.comments = []
        agent.follows = []
        agent.generated_bio = ""
        agents.append(agent)

    return agents
