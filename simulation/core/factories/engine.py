"""Factory for creating the simulation engine."""

from collections.abc import Callable

from db.adapters.base import TransactionProvider
from db.adapters.sqlite.sqlite import SqliteTransactionProvider
from db.repositories.comment_repository import create_sqlite_comment_repository
from db.repositories.feed_post_repository import create_sqlite_feed_post_repository
from db.repositories.follow_repository import create_sqlite_follow_repository
from db.repositories.generated_bio_repository import (
    create_sqlite_generated_bio_repository,
)
from db.repositories.generated_feed_repository import (
    create_sqlite_generated_feed_repository,
)
from db.repositories.interfaces import (
    CommentRepository,
    FeedPostRepository,
    FollowRepository,
    GeneratedBioRepository,
    GeneratedFeedRepository,
    LikeRepository,
    MetricsRepository,
    ProfileRepository,
    RunRepository,
)
from db.repositories.like_repository import create_sqlite_like_repository
from db.repositories.metrics_repository import create_sqlite_metrics_repository
from db.repositories.profile_repository import create_sqlite_profile_repository
from db.repositories.run_repository import create_sqlite_repository
from db.services.simulation_persistence_service import (
    create_simulation_persistence_service,
)
from simulation.core.action_history import (
    ActionHistoryStore,
    create_default_action_history_store_factory,
)
from simulation.core.engine import SimulationEngine
from simulation.core.factories.agent import create_default_agent_factory
from simulation.core.factories.command_service import create_command_service
from simulation.core.factories.query_service import create_query_service
from simulation.core.models.agents import SocialMediaAgent


def create_engine(
    *,
    run_repo: RunRepository | None = None,
    metrics_repo: MetricsRepository | None = None,
    profile_repo: ProfileRepository | None = None,
    feed_post_repo: FeedPostRepository | None = None,
    generated_bio_repo: GeneratedBioRepository | None = None,
    generated_feed_repo: GeneratedFeedRepository | None = None,
    like_repo: LikeRepository | None = None,
    comment_repo: CommentRepository | None = None,
    follow_repo: FollowRepository | None = None,
    agent_factory: Callable[[int], list[SocialMediaAgent]] | None = None,
    action_history_store_factory: Callable[[], ActionHistoryStore] | None = None,
    transaction_provider: TransactionProvider | None = None,
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
        like_repo: Optional. Like repository. Defaults to SQLite implementation.
        comment_repo: Optional. Comment repository. Defaults to SQLite implementation.
        follow_repo: Optional. Follow repository. Defaults to SQLite implementation.
        agent_factory: Optional. Agent factory function. Defaults to create_default_agent_factory().
        transaction_provider: Optional. Provider for persistence transactions. Defaults to SQLite.

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
    # Create transaction_provider first (needed by run_repo and metrics_repo)
    if transaction_provider is None:
        transaction_provider = SqliteTransactionProvider()

    # Create default repositories if not provided
    if run_repo is None:
        run_repo = create_sqlite_repository(transaction_provider=transaction_provider)
    if metrics_repo is None:
        metrics_repo = create_sqlite_metrics_repository(
            transaction_provider=transaction_provider
        )
    if profile_repo is None:
        profile_repo = create_sqlite_profile_repository(
            transaction_provider=transaction_provider
        )
    if feed_post_repo is None:
        feed_post_repo = create_sqlite_feed_post_repository(
            transaction_provider=transaction_provider
        )
    if generated_bio_repo is None:
        generated_bio_repo = create_sqlite_generated_bio_repository(
            transaction_provider=transaction_provider
        )
    if generated_feed_repo is None:
        generated_feed_repo = create_sqlite_generated_feed_repository(
            transaction_provider=transaction_provider
        )

    # Create default agent factory if not provided
    if agent_factory is None:
        agent_factory = create_default_agent_factory()
    if action_history_store_factory is None:
        action_history_store_factory = create_default_action_history_store_factory()

    if like_repo is None:
        like_repo = create_sqlite_like_repository(
            transaction_provider=transaction_provider
        )
    if comment_repo is None:
        comment_repo = create_sqlite_comment_repository(
            transaction_provider=transaction_provider
        )
    if follow_repo is None:
        follow_repo = create_sqlite_follow_repository(
            transaction_provider=transaction_provider
        )
    query_service = create_query_service(
        run_repo=run_repo,
        metrics_repo=metrics_repo,
        feed_post_repo=feed_post_repo,
        generated_feed_repo=generated_feed_repo,
        like_repo=like_repo,
        comment_repo=comment_repo,
        follow_repo=follow_repo,
    )
    simulation_persistence = create_simulation_persistence_service(
        run_repo=run_repo,
        metrics_repo=metrics_repo,
        transaction_provider=transaction_provider,
        like_repo=like_repo,
        comment_repo=comment_repo,
        follow_repo=follow_repo,
    )
    command_service = create_command_service(
        run_repo=run_repo,
        metrics_repo=metrics_repo,
        simulation_persistence=simulation_persistence,
        profile_repo=profile_repo,
        feed_post_repo=feed_post_repo,
        generated_bio_repo=generated_bio_repo,
        generated_feed_repo=generated_feed_repo,
        agent_factory=agent_factory,
        action_history_store_factory=action_history_store_factory,
    )

    return SimulationEngine(
        run_repo=run_repo,
        metrics_repo=metrics_repo,
        profile_repo=profile_repo,
        feed_post_repo=feed_post_repo,
        generated_bio_repo=generated_bio_repo,
        generated_feed_repo=generated_feed_repo,
        agent_factory=agent_factory,
        action_history_store_factory=action_history_store_factory,
        query_service=query_service,
        command_service=command_service,
    )
