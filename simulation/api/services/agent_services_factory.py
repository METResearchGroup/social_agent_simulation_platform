"""Factory for creating agent query and command services with optional dependency injection."""

from db.adapters.base import TransactionProvider
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
from simulation.api.services.agent_command_service import AgentCommandService
from simulation.api.services.agent_query_service import AgentQueryService


def create_agent_query_service(
    *,
    agent_repo: AgentRepository | None = None,
    bio_repo: AgentBioRepository | None = None,
    metadata_repo: UserAgentProfileMetadataRepository | None = None,
) -> AgentQueryService:
    """Create AgentQueryService with optional injected repositories.

    When a repository is not provided, defaults to SQLite implementation.
    """
    if agent_repo is None:
        agent_repo = create_sqlite_agent_repository()
    if bio_repo is None:
        bio_repo = create_sqlite_agent_bio_repository()
    if metadata_repo is None:
        metadata_repo = create_sqlite_user_agent_profile_metadata_repository()
    return AgentQueryService(
        agent_repo=agent_repo,
        bio_repo=bio_repo,
        metadata_repo=metadata_repo,
    )


def create_agent_command_service(
    *,
    agent_repo: AgentRepository | None = None,
    bio_repo: AgentBioRepository | None = None,
    metadata_repo: UserAgentProfileMetadataRepository | None = None,
    transaction_provider: TransactionProvider | None = None,
) -> AgentCommandService:
    """Create AgentCommandService with optional injected dependencies.

    When a dependency is not provided, defaults to SQLite implementation.
    """
    if agent_repo is None:
        agent_repo = create_sqlite_agent_repository()
    if bio_repo is None:
        bio_repo = create_sqlite_agent_bio_repository()
    if metadata_repo is None:
        metadata_repo = create_sqlite_user_agent_profile_metadata_repository()
    if transaction_provider is None:
        transaction_provider = SqliteTransactionProvider()
    return AgentCommandService(
        agent_repo=agent_repo,
        bio_repo=bio_repo,
        metadata_repo=metadata_repo,
        transaction_provider=transaction_provider,
    )
