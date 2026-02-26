"""Write-side CQRS service for simulation agent creation."""

import uuid

from db.adapters.base import TransactionProvider
from db.repositories.interfaces import (
    AgentBioRepository,
    AgentRepository,
    UserAgentProfileMetadataRepository,
)
from lib.timestamp_utils import get_current_timestamp
from simulation.api.errors import ApiHandleAlreadyExistsError
from simulation.api.schemas.simulation import AgentSchema, CreateAgentRequest
from simulation.core.handle_utils import normalize_handle
from simulation.core.models.agent import Agent, PersonaSource
from simulation.core.models.agent_bio import AgentBio, PersonaBioSource
from simulation.core.models.user_agent_profile_metadata import UserAgentProfileMetadata


def create_agent(
    req: CreateAgentRequest,
    *,
    transaction_provider: TransactionProvider,
    agent_repo: AgentRepository,
    bio_repo: AgentBioRepository,
    metadata_repo: UserAgentProfileMetadataRepository,
) -> AgentSchema:
    """Create a user-generated agent with bio and metadata. Atomic multi-table write."""
    handle = normalize_handle(req.handle)
    display_name = req.display_name.strip()
    bio_text = (req.bio or "").strip() or "No bio provided."

    # TODO: that this can cause a slight race condition if we do this check
    # before the below context manager for writing the agent to the database.
    # This is a known issue, and we'll revisit this in the future.
    if agent_repo.get_agent_by_handle(handle) is not None:
        raise ApiHandleAlreadyExistsError(handle)

    agent_id = _generate_agent_id()
    now = get_current_timestamp()

    agent = _generate_agent(agent_id, handle, display_name, now)
    agent_bio = _generate_agent_bio(agent_id, bio_text, now)
    metadata = _generate_user_agent_profile_metadata(agent_id, now)

    with transaction_provider.run_transaction() as conn:
        agent_repo.create_or_update_agent(agent, conn=conn)
        bio_repo.create_agent_bio(agent_bio, conn=conn)
        metadata_repo.create_or_update_metadata(metadata, conn=conn)

    return _build_agent_schema(agent.handle, agent.display_name, bio_text)


def _build_agent_schema(handle: str, display_name: str, bio_text: str) -> AgentSchema:
    """Build AgentSchema for a newly created agent (zero counts)."""
    return AgentSchema(
        handle=handle,
        name=display_name,
        bio=bio_text,
        generated_bio="",
        followers=0,
        following=0,
        posts_count=0,
    )


def _generate_agent_id() -> str:
    """Generate a new unique agent ID."""
    return uuid.uuid4().hex


def _generate_agent(
    agent_id: str, handle: str, display_name: str, timestamp: str
) -> Agent:
    """Build an Agent model for user-generated creation."""
    return Agent(
        agent_id=agent_id,
        handle=handle,
        persona_source=PersonaSource.USER_GENERATED,
        display_name=display_name,
        created_at=timestamp,
        updated_at=timestamp,
    )


def _generate_agent_bio(agent_id: str, bio_text: str, timestamp: str) -> AgentBio:
    """Build an AgentBio model for user-provided creation."""
    return AgentBio(
        id=uuid.uuid4().hex,
        agent_id=agent_id,
        persona_bio=bio_text,
        persona_bio_source=PersonaBioSource.USER_PROVIDED,
        created_at=timestamp,
        updated_at=timestamp,
    )


def _generate_user_agent_profile_metadata(
    agent_id: str, timestamp: str
) -> UserAgentProfileMetadata:
    """Build UserAgentProfileMetadata with zero counts for new agents."""
    return UserAgentProfileMetadata(
        id=uuid.uuid4().hex,
        agent_id=agent_id,
        followers_count=0,
        follows_count=0,
        posts_count=0,
        created_at=timestamp,
        updated_at=timestamp,
    )
