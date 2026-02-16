"""Factory for creating the simulation engine."""

from collections.abc import Callable
from typing import Optional

from db.repositories.feed_post_repository import create_sqlite_feed_post_repository
from db.repositories.generated_bio_repository import (
    create_sqlite_generated_bio_repository,
)
from db.repositories.generated_feed_repository import (
    create_sqlite_generated_feed_repository,
)
from db.repositories.profile_repository import create_sqlite_profile_repository
from db.repositories.run_repository import create_sqlite_repository
from db.repositories.interfaces import (
    FeedPostRepository,
    GeneratedBioRepository,
    GeneratedFeedRepository,
    ProfileRepository,
    RunRepository,
)
from simulation.core.action_history import ActionHistoryStore
from simulation.core.engine import SimulationEngine
from simulation.core.models.agents import SocialMediaAgent

from .agent import create_default_agent_factory
from .action_history_store import create_default_action_history_store_factory
from .command_service import create_command_service
from .query_service import create_query_service


def create_engine(
    *,
    run_repo: Optional[RunRepository] = None,
    profile_repo: Optional[ProfileRepository] = None,
    feed_post_repo: Optional[FeedPostRepository] = None,
    generated_bio_repo: Optional[GeneratedBioRepository] = None,
    generated_feed_repo: Optional[GeneratedFeedRepository] = None,
    agent_factory: Optional[Callable[[int], list[SocialMediaAgent]]] = None,
    action_history_store_factory: Optional[Callable[[], ActionHistoryStore]] = None,
) -> SimulationEngine:
    """Create a SimulationEngine with injected dependencies.

    This factory function creates a SimulationEngine instance with all required
    dependencies. If a dependency is not provided, it defaults to creating a
    SQLite repository or the default agent factory.

    Args:
        run_repo: Optional. Run repository. Defaults to SQLite implementation.
        profile_repo: Optional. Profile repository. Defaults to SQLite implementation.
        feed_post_repo: Optional. Feed post repository. Defaults to SQLite implementation.
        generated_bio_repo: Optional. Generated bio repository. Defaults to SQLite implementation.
        generated_feed_repo: Optional. Generated feed repository. Defaults to SQLite implementation.
        agent_factory: Optional. Agent factory function. Defaults to create_default_agent_factory().

    Returns:
        A configured SimulationEngine instance.

    Example:
        >>> # Use all defaults
        >>> engine = create_engine()
        >>>
        >>> # Override specific dependencies
        >>> engine = create_engine(
        ...     run_repo=my_custom_repo,
        ...     agent_factory=my_custom_factory,
        ... )
    """
    # Create default repositories if not provided
    if run_repo is None:
        run_repo = create_sqlite_repository()
    if profile_repo is None:
        profile_repo = create_sqlite_profile_repository()
    if feed_post_repo is None:
        feed_post_repo = create_sqlite_feed_post_repository()
    if generated_bio_repo is None:
        generated_bio_repo = create_sqlite_generated_bio_repository()
    if generated_feed_repo is None:
        generated_feed_repo = create_sqlite_generated_feed_repository()

    # Create default agent factory if not provided
    if agent_factory is None:
        agent_factory = create_default_agent_factory()
    if action_history_store_factory is None:
        action_history_store_factory = create_default_action_history_store_factory()

    query_service = create_query_service(
        run_repo=run_repo,
        feed_post_repo=feed_post_repo,
        generated_feed_repo=generated_feed_repo,
    )
    command_service = create_command_service(
        run_repo=run_repo,
        profile_repo=profile_repo,
        feed_post_repo=feed_post_repo,
        generated_bio_repo=generated_bio_repo,
        generated_feed_repo=generated_feed_repo,
        agent_factory=agent_factory,
        action_history_store_factory=action_history_store_factory,
    )

    return SimulationEngine(
        run_repo=run_repo,
        profile_repo=profile_repo,
        feed_post_repo=feed_post_repo,
        generated_bio_repo=generated_bio_repo,
        generated_feed_repo=generated_feed_repo,
        agent_factory=agent_factory,
        query_service=query_service,
        command_service=command_service,
    )
