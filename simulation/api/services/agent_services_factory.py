"""Factory for creating agent query and command services with injected dependencies."""

from db.adapters.base import TransactionProvider
from db.repositories.interfaces import (
    AgentBioRepository,
    AgentRepository,
    UserAgentProfileMetadataRepository,
)
from simulation.api.services.agent_command_service import AgentCommandService
from simulation.api.services.agent_query_service import AgentQueryService


def create_agent_query_service(
    *,
    agent_repo: AgentRepository,
    bio_repo: AgentBioRepository,
    metadata_repo: UserAgentProfileMetadataRepository,
) -> AgentQueryService:
    """Create AgentQueryService by wiring the provided repositories."""
    return AgentQueryService(
        agent_repo=agent_repo,
        bio_repo=bio_repo,
        metadata_repo=metadata_repo,
    )


def create_agent_command_service(
    *,
    agent_repo: AgentRepository,
    bio_repo: AgentBioRepository,
    metadata_repo: UserAgentProfileMetadataRepository,
    transaction_provider: TransactionProvider,
) -> AgentCommandService:
    """Create AgentCommandService by wiring the provided dependencies."""
    return AgentCommandService(
        agent_repo=agent_repo,
        bio_repo=bio_repo,
        metadata_repo=metadata_repo,
        transaction_provider=transaction_provider,
    )
