"""Write-side CQRS service for simulation agent creation."""

import uuid

from db.adapters.sqlite.sqlite import SqliteTransactionProvider
from db.repositories.agent_bio_repository import create_sqlite_agent_bio_repository
from db.repositories.agent_repository import create_sqlite_agent_repository
from db.repositories.user_agent_profile_metadata_repository import (
    create_sqlite_user_agent_profile_metadata_repository,
)
from lib.timestamp_utils import get_current_timestamp
from simulation.api.schemas.simulation import AgentSchema, CreateAgentRequest
from simulation.core.exceptions import HandleAlreadyExistsError
from simulation.core.handle_utils import normalize_handle
from simulation.core.models.agent import Agent, PersonaSource
from simulation.core.models.agent_bio import AgentBio, PersonaBioSource
from simulation.core.models.user_agent_profile_metadata import UserAgentProfileMetadata


def create_agent(req: CreateAgentRequest) -> AgentSchema:
    """Create a user-generated agent with bio and metadata. Atomic multi-table write."""
    handle = normalize_handle(req.handle)
    display_name = req.display_name.strip()
    bio_text = (req.bio or "").strip() or "No bio provided."

    agent_repo = create_sqlite_agent_repository()
    bio_repo = create_sqlite_agent_bio_repository()
    metadata_repo = create_sqlite_user_agent_profile_metadata_repository()

    if agent_repo.get_agent_by_handle(handle) is not None:
        raise HandleAlreadyExistsError(handle)

    agent_id = uuid.uuid4().hex
    now = get_current_timestamp()

    agent = Agent(
        agent_id=agent_id,
        handle=handle,
        persona_source=PersonaSource.USER_GENERATED,
        display_name=display_name,
        created_at=now,
        updated_at=now,
    )
    agent_bio = AgentBio(
        id=uuid.uuid4().hex,
        agent_id=agent_id,
        persona_bio=bio_text,
        persona_bio_source=PersonaBioSource.USER_PROVIDED,
        created_at=now,
        updated_at=now,
    )
    metadata = UserAgentProfileMetadata(
        id=uuid.uuid4().hex,
        agent_id=agent_id,
        followers_count=0,
        follows_count=0,
        posts_count=0,
        created_at=now,
        updated_at=now,
    )

    provider = SqliteTransactionProvider()
    with provider.run_transaction() as conn:
        agent_repo.create_or_update_agent(agent, conn=conn)
        bio_repo.create_agent_bio(agent_bio, conn=conn)
        metadata_repo.create_or_update_metadata(metadata, conn=conn)

    return AgentSchema(
        handle=agent.handle,
        name=agent.display_name,
        bio=bio_text,
        generated_bio="",
        followers=0,
        following=0,
        posts_count=0,
    )
