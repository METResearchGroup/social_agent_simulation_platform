"""Factory for creating the simulation command service."""

from collections.abc import Callable
from dataclasses import dataclass

from db.adapters.base import TransactionProvider
from db.repositories.interfaces import (
    AgentBioRepository,
    AgentFollowEdgeRepository,
    AgentPostLikeRepository,
    AgentPostRepository,
    AgentRepository,
    FeedPostRepository,
    GeneratedFeedRepository,
    MetricsRepository,
    ProfileRepository,
    RunAgentRepository,
    RunFollowEdgeRepository,
    RunPostLikeRepository,
    RunPostRepository,
    RunRepository,
    UserAgentProfileMetadataRepository,
)
from db.services.simulation_persistence_service import SimulationPersistenceService
from feeds.feed_generator_adapter import FeedGeneratorAdapter
from feeds.interfaces import FeedGenerator
from simulation.core.action_history import (
    ActionHistoryStore,
    create_default_action_history_store_factory,
)
from simulation.core.action_policy import (
    AgentActionFeedFilter,
    AgentActionRulesValidator,
    HistoryAwareActionFeedFilter,
)
from simulation.core.command_service import SimulationCommandService
from simulation.core.metrics.collector import MetricsCollector
from simulation.core.metrics.defaults import (
    DEFAULT_RUN_METRIC_KEYS,
    DEFAULT_TURN_METRIC_KEYS,
    create_default_metrics_registry,
)
from simulation.core.metrics.interfaces import MetricDeps
from simulation.core.metrics.registry import MetricsRegistry
from simulation.core.models.agents import SimulationAgent


@dataclass(frozen=True, slots=True)
class CommandServiceRepos:
    """Repositories and transaction wiring for command-side simulation execution.

    Groups persistence collaborators so callers do not pass a long flat list of
    repository parameters. Seed-state (`Agent*`) and run snapshot (`Run*`) repos
    match the scopes described in ``docs/architecture/agents-turns-runs-data-model.md``.
    """

    run_repo: RunRepository
    metrics_repo: MetricsRepository
    profile_repo: ProfileRepository
    feed_post_repo: FeedPostRepository
    generated_feed_repo: GeneratedFeedRepository
    agent_repo: AgentRepository
    agent_bio_repo: AgentBioRepository
    agent_follow_edge_repo: AgentFollowEdgeRepository
    user_agent_profile_metadata_repo: UserAgentProfileMetadataRepository
    run_agent_repo: RunAgentRepository
    run_follow_edge_repo: RunFollowEdgeRepository
    run_post_repo: RunPostRepository
    run_post_like_repo: RunPostLikeRepository
    agent_post_repo: AgentPostRepository
    agent_post_like_repo: AgentPostLikeRepository
    transaction_provider: TransactionProvider


def _default_feed_generator(repos: CommandServiceRepos) -> FeedGenerator:
    return FeedGeneratorAdapter(
        generated_feed_repo=repos.generated_feed_repo,
        run_post_repo=repos.run_post_repo,
        run_post_like_repo=repos.run_post_like_repo,
    )


def _default_metrics_collector(repos: CommandServiceRepos) -> MetricsCollector:
    registry: MetricsRegistry = create_default_metrics_registry()
    deps = MetricDeps(
        run_repo=repos.run_repo, metrics_repo=repos.metrics_repo, sql_executor=None
    )
    return MetricsCollector(
        registry=registry,
        turn_metric_keys=DEFAULT_TURN_METRIC_KEYS,
        run_metric_keys=DEFAULT_RUN_METRIC_KEYS,
        deps=deps,
    )


def create_command_service(
    *,
    repos: CommandServiceRepos,
    simulation_persistence: SimulationPersistenceService,
    agent_factory: Callable[[int], list[SimulationAgent]],
    action_history_store_factory: Callable[[], ActionHistoryStore] | None = None,
    feed_generator: FeedGenerator | None = None,
    metrics_collector: MetricsCollector | None = None,
    agent_action_rules_validator: AgentActionRulesValidator | None = None,
    agent_action_feed_filter: AgentActionFeedFilter | None = None,
) -> SimulationCommandService:
    """Create command-side service with execution dependencies."""
    if action_history_store_factory is None:
        action_history_store_factory = create_default_action_history_store_factory()
    if feed_generator is None:
        feed_generator = _default_feed_generator(repos)

    if metrics_collector is None:
        metrics_collector = _default_metrics_collector(repos)

    return SimulationCommandService(
        run_repo=repos.run_repo,
        metrics_repo=repos.metrics_repo,
        metrics_collector=metrics_collector,
        simulation_persistence=simulation_persistence,
        profile_repo=repos.profile_repo,
        feed_post_repo=repos.feed_post_repo,
        generated_feed_repo=repos.generated_feed_repo,
        agent_repo=repos.agent_repo,
        agent_bio_repo=repos.agent_bio_repo,
        agent_follow_edge_repo=repos.agent_follow_edge_repo,
        user_agent_profile_metadata_repo=repos.user_agent_profile_metadata_repo,
        run_agent_repo=repos.run_agent_repo,
        run_follow_edge_repo=repos.run_follow_edge_repo,
        run_post_repo=repos.run_post_repo,
        run_post_like_repo=repos.run_post_like_repo,
        agent_post_repo=repos.agent_post_repo,
        agent_post_like_repo=repos.agent_post_like_repo,
        transaction_provider=repos.transaction_provider,
        agent_factory=agent_factory,
        action_history_store_factory=action_history_store_factory,
        feed_generator=feed_generator,
        agent_action_rules_validator=agent_action_rules_validator
        or AgentActionRulesValidator(),
        agent_action_feed_filter=agent_action_feed_filter
        or HistoryAwareActionFeedFilter(),
    )
