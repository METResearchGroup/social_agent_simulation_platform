"""Read-side CQRS service for simulation agent lookup APIs."""

from db.adapters.sqlite.sqlite import SqliteTransactionProvider
from db.repositories.agent_bio_repository import create_sqlite_agent_bio_repository
from db.repositories.agent_repository import create_sqlite_agent_repository
from db.repositories.interfaces import (
    AgentBioRepository,
    AgentRepository,
    UserAgentProfileMetadataRepository,
)
from db.repositories.user_agent_profile_metadata_repository import (
    create_sqlite_user_agent_profile_metadata_repository,
)
from lib.sql_like import build_substring_like_pattern_from_user_query
from simulation.api.schemas.simulation import AgentSchema
from simulation.core.models.agent import Agent
from simulation.core.models.agent_bio import AgentBio
from simulation.core.models.user_agent_profile_metadata import UserAgentProfileMetadata


def list_agents(
    *,
    agent_repo: AgentRepository | None = None,
    bio_repo: AgentBioRepository | None = None,
    metadata_repo: UserAgentProfileMetadataRepository | None = None,
    q: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[AgentSchema]:
    """Return agents from DB, mapped to AgentSchema, ordered by handle."""
    if agent_repo is None or bio_repo is None or metadata_repo is None:
        provider = SqliteTransactionProvider()
        agent_repo = agent_repo or create_sqlite_agent_repository(
            transaction_provider=provider
        )
        bio_repo = bio_repo or create_sqlite_agent_bio_repository(
            transaction_provider=provider
        )
        metadata_repo = metadata_repo or (
            create_sqlite_user_agent_profile_metadata_repository(
                transaction_provider=provider
            )
        )

    handle_like: str | None = build_substring_like_pattern_from_user_query(q)

    agents: list[Agent]
    if limit is None:
        if offset != 0:
            raise ValueError("offset requires limit to be set")
        if handle_like is not None:
            raise ValueError("q requires limit to be set")
        agents = agent_repo.list_all_agents()
    else:
        if handle_like is None:
            agents = agent_repo.list_agents_page(limit=limit, offset=offset)
        else:
            agents = agent_repo.search_agents_page(
                handle_like=handle_like, limit=limit, offset=offset
            )

    return _hydrate_agents(
        agents=agents, bio_repo=bio_repo, metadata_repo=metadata_repo
    )


def _hydrate_agents(
    *,
    agents: list[Agent],
    bio_repo: AgentBioRepository,
    metadata_repo: UserAgentProfileMetadataRepository,
) -> list[AgentSchema]:
    """Hydrate agents with latest bio + metadata (batch) and map to AgentSchema."""
    if not agents:
        return []

    agent_ids = [a.agent_id for a in agents]
    bio_map = bio_repo.get_latest_bios_by_agent_ids(agent_ids)
    metadata_map = metadata_repo.get_metadata_by_agent_ids(agent_ids)

    return [_agent_to_schema(agent, bio_map, metadata_map) for agent in agents]


def _agent_to_schema(
    agent: Agent,
    bio_map: dict[str, AgentBio | None],
    metadata_map: dict[str, UserAgentProfileMetadata | None],
) -> AgentSchema:
    """Map a single agent plus pre-fetched bio/metadata to AgentSchema."""
    bio = bio_map.get(agent.agent_id)
    metadata = metadata_map.get(agent.agent_id)

    persona_bio = bio.persona_bio if bio else ""
    followers = metadata.followers_count if metadata else 0
    follows = metadata.follows_count if metadata else 0
    posts_count = metadata.posts_count if metadata else 0

    return AgentSchema(
        handle=agent.handle,
        name=agent.display_name,
        bio=persona_bio,
        generated_bio="",
        followers=followers,
        following=follows,
        posts_count=posts_count,
    )
