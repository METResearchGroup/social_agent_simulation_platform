"""App context: bundles repository dependencies for lifespan and request handling.

Single container assigned to app.state.deps. Centralises wiring and simplifies
adding new repositories as the codebase grows.
"""

from __future__ import annotations

from dataclasses import dataclass

from db.adapters.base import TransactionProvider
from db.adapters.sqlite.sqlite import SqliteTransactionProvider
from db.repositories.agent_bio_repository import create_sqlite_agent_bio_repository
from db.repositories.agent_follow_edge_repository import (
    create_sqlite_agent_follow_edge_repository,
)
from db.repositories.agent_repository import create_sqlite_agent_repository
from db.repositories.app_user_repository import create_sqlite_app_user_repository
from db.repositories.interfaces import (
    AgentBioRepository,
    AgentFollowEdgeRepository,
    AgentRepository,
    AppUserRepository,
    RunAgentRepository,
    RunFollowEdgeRepository,
    UserAgentProfileMetadataRepository,
)
from db.repositories.run_agent_repository import create_sqlite_run_agent_repository
from db.repositories.run_follow_edge_repository import (
    create_sqlite_run_follow_edge_repository,
)
from db.repositories.user_agent_profile_metadata_repository import (
    create_sqlite_user_agent_profile_metadata_repository,
)
from simulation.core.engine import SimulationEngine
from simulation.core.factories import create_engine


@dataclass
class AppContext:
    """Bundles transaction provider, repositories, and engine for app-wide use."""

    transaction_provider: TransactionProvider
    agent_repo: AgentRepository
    agent_bio_repo: AgentBioRepository
    agent_metadata_repo: UserAgentProfileMetadataRepository
    agent_follow_edge_repo: AgentFollowEdgeRepository
    run_agent_repo: RunAgentRepository
    run_follow_edge_repo: RunFollowEdgeRepository
    app_user_repository: AppUserRepository
    engine: SimulationEngine


def build_app_context() -> AppContext:
    """Create transaction provider, repositories, and engine; return bundled AppContext."""
    transaction_provider = SqliteTransactionProvider()
    agent_repo = create_sqlite_agent_repository(
        transaction_provider=transaction_provider
    )
    agent_bio_repo = create_sqlite_agent_bio_repository(
        transaction_provider=transaction_provider
    )
    agent_metadata_repo = create_sqlite_user_agent_profile_metadata_repository(
        transaction_provider=transaction_provider
    )
    agent_follow_edge_repo = create_sqlite_agent_follow_edge_repository(
        transaction_provider=transaction_provider
    )
    run_agent_repo = create_sqlite_run_agent_repository(
        transaction_provider=transaction_provider
    )
    run_follow_edge_repo = create_sqlite_run_follow_edge_repository(
        transaction_provider=transaction_provider
    )
    app_user_repository = create_sqlite_app_user_repository()

    engine = create_engine(
        transaction_provider=transaction_provider,
        agent_repo=agent_repo,
        agent_bio_repo=agent_bio_repo,
        agent_follow_edge_repo=agent_follow_edge_repo,
        user_agent_profile_metadata_repo=agent_metadata_repo,
        run_agent_repo=run_agent_repo,
        run_follow_edge_repo=run_follow_edge_repo,
    )

    return AppContext(
        transaction_provider=transaction_provider,
        agent_repo=agent_repo,
        agent_bio_repo=agent_bio_repo,
        agent_metadata_repo=agent_metadata_repo,
        agent_follow_edge_repo=agent_follow_edge_repo,
        run_agent_repo=run_agent_repo,
        run_follow_edge_repo=run_follow_edge_repo,
        app_user_repository=app_user_repository,
        engine=engine,
    )
