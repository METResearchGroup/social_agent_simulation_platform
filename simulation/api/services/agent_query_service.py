"""Read-side CQRS service for simulation agent lookup APIs."""

from db.adapters.sqlite.sqlite import SqliteTransactionProvider
from db.repositories.agent_bio_repository import create_sqlite_agent_bio_repository
from db.repositories.agent_liked_post_repository import (
    create_sqlite_agent_liked_post_repository,
)
from db.repositories.agent_linked_agent_repository import (
    create_sqlite_agent_linked_agent_repository,
)
from db.repositories.agent_profile_comment_repository import (
    create_sqlite_agent_profile_comment_repository,
)
from db.repositories.agent_repository import create_sqlite_agent_repository
from db.repositories.interfaces import (
    AgentBioRepository,
    AgentLikedPostRepository,
    AgentLinkedAgentRepository,
    AgentProfileCommentRepository,
    AgentRepository,
    UserAgentProfileMetadataRepository,
)
from db.repositories.user_agent_profile_metadata_repository import (
    create_sqlite_user_agent_profile_metadata_repository,
)
from simulation.api.dummy_data import DUMMY_AGENTS
from simulation.api.schemas.simulation import AgentSchema, CommentEntry
from simulation.core.models.agent import Agent
from simulation.core.models.agent_bio import AgentBio
from simulation.core.models.agent_liked_post import AgentLikedPost
from simulation.core.models.agent_linked_agent import AgentLinkedAgent
from simulation.core.models.agent_profile_comment import AgentProfileComment
from simulation.core.models.user_agent_profile_metadata import UserAgentProfileMetadata


def list_agents(
    *,
    agent_repo: AgentRepository | None = None,
    bio_repo: AgentBioRepository | None = None,
    metadata_repo: UserAgentProfileMetadataRepository | None = None,
    comment_repo: AgentProfileCommentRepository | None = None,
    liked_post_repo: AgentLikedPostRepository | None = None,
    linked_agent_repo: AgentLinkedAgentRepository | None = None,
) -> list[AgentSchema]:
    """Return agents from DB, mapped to AgentSchema, ordered by handle."""
    if (
        agent_repo is None
        or bio_repo is None
        or metadata_repo is None
        or comment_repo is None
        or liked_post_repo is None
        or linked_agent_repo is None
    ):
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
        comment_repo = comment_repo or create_sqlite_agent_profile_comment_repository(
            transaction_provider=provider
        )
        liked_post_repo = liked_post_repo or create_sqlite_agent_liked_post_repository(
            transaction_provider=provider
        )
        linked_agent_repo = linked_agent_repo or (
            create_sqlite_agent_linked_agent_repository(transaction_provider=provider)
        )

    agents = agent_repo.list_all_agents()
    if not agents:
        return []

    agent_ids = [a.agent_id for a in agents]
    bio_map = bio_repo.get_latest_bios_by_agent_ids(agent_ids)
    metadata_map = metadata_repo.get_metadata_by_agent_ids(agent_ids)
    comments_map = comment_repo.get_comments_by_agent_ids(agent_ids)
    liked_posts_map = liked_post_repo.get_liked_posts_by_agent_ids(agent_ids)
    linked_agents_map = linked_agent_repo.get_linked_agents_by_agent_ids(agent_ids)

    return [
        _agent_to_schema(
            agent,
            bio_map,
            metadata_map,
            comments_map,
            liked_posts_map,
            linked_agents_map,
        )
        for agent in agents
    ]


def _agent_to_schema(
    agent: Agent,
    bio_map: dict[str, AgentBio | None],
    metadata_map: dict[str, UserAgentProfileMetadata | None],
    comments_map: dict[str, list[AgentProfileComment]],
    liked_posts_map: dict[str, list[AgentLikedPost]],
    linked_agents_map: dict[str, list[AgentLinkedAgent]],
) -> AgentSchema:
    """Map a single agent plus pre-fetched data to AgentSchema."""
    bio = bio_map.get(agent.agent_id)
    metadata = metadata_map.get(agent.agent_id)
    comments = comments_map.get(agent.agent_id, [])
    liked_posts = liked_posts_map.get(agent.agent_id, [])
    linked_agents = linked_agents_map.get(agent.agent_id, [])

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
        comments=[CommentEntry(text=c.text, post_uri=c.post_uri) for c in comments],
        liked_post_uris=[lp.post_uri for lp in liked_posts],
        linked_agent_handles=[la.linked_agent_handle for la in linked_agents],
    )


def list_agents_dummy() -> list[AgentSchema]:
    """Return deterministic dummy agent list for run-detail mock endpoint, sorted by handle."""
    return sorted(DUMMY_AGENTS, key=lambda a: a.handle)
