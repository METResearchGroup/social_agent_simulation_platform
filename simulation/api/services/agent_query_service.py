"""Read-side CQRS service for simulation agent lookup APIs."""

from db.repositories.agent_bio_repository import create_sqlite_agent_bio_repository
from db.repositories.agent_repository import create_sqlite_agent_repository
from db.repositories.user_agent_profile_metadata_repository import (
    create_sqlite_user_agent_profile_metadata_repository,
)
from simulation.api.dummy_data import DUMMY_AGENTS
from simulation.api.schemas.simulation import AgentSchema


def list_agents() -> list[AgentSchema]:
    """Return agents from DB, mapped to AgentSchema, sorted by handle."""
    agent_repo = create_sqlite_agent_repository()
    bio_repo = create_sqlite_agent_bio_repository()
    metadata_repo = create_sqlite_user_agent_profile_metadata_repository()

    agents = agent_repo.list_all_agents()
    result: list[AgentSchema] = []

    for agent in agents:
        bio = bio_repo.get_latest_agent_bio(agent.agent_id)
        metadata = metadata_repo.get_by_agent_id(agent.agent_id)

        persona_bio = bio.persona_bio if bio else ""
        followers = metadata.followers_count if metadata else 0
        follows = metadata.follows_count if metadata else 0
        posts_count = metadata.posts_count if metadata else 0

        result.append(
            AgentSchema(
                handle=agent.handle,
                name=agent.display_name,
                bio=persona_bio,
                generated_bio="",
                followers=followers,
                following=follows,
                posts_count=posts_count,
            )
        )

    return sorted(result, key=lambda a: a.handle)


def list_agents_dummy() -> list[AgentSchema]:
    """Return deterministic dummy agent list for run-detail mock endpoint, sorted by handle."""
    return sorted(DUMMY_AGENTS, key=lambda a: a.handle)
