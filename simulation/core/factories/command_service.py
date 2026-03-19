"""Factory for creating the simulation command service."""

from collections.abc import Callable

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
from simulation.core.metrics.collector import MetricsCollector
from simulation.core.metrics.defaults import (
    DEFAULT_RUN_METRIC_KEYS,
    DEFAULT_TURN_METRIC_KEYS,
    create_default_metrics_registry,
)
from simulation.core.metrics.interfaces import MetricDeps
from simulation.core.metrics.registry import MetricsRegistry
from simulation.core.models.agents import SimulationAgent
from simulation.core.services.command_service import SimulationCommandService
from simulation.core.services.command_service_bundles import (
    CommandServiceRepos,
    CommandServiceRuntime,
)


def _default_feed_generator(repos: CommandServiceRepos) -> FeedGenerator:
    return FeedGeneratorAdapter(
        generated_feed_repo=repos.turn.generated_feed_repo,
        run_post_repo=repos.run.run_post_repo,
        run_post_like_repo=repos.run.run_post_like_repo,
    )


def _default_metrics_collector(repos: CommandServiceRepos) -> MetricsCollector:
    registry: MetricsRegistry = create_default_metrics_registry()
    deps = MetricDeps(
        run_repo=repos.run.run_repo,
        metrics_repo=repos.run.metrics_repo,
        sql_executor=None,
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
        repos=repos,
        metrics_collector=metrics_collector,
        simulation_persistence=simulation_persistence,
        runtime=CommandServiceRuntime(
            agent_factory=agent_factory,
            action_history_store_factory=action_history_store_factory,
            feed_generator=feed_generator,
            agent_action_rules_validator=agent_action_rules_validator
            or AgentActionRulesValidator(),
            agent_action_feed_filter=agent_action_feed_filter
            or HistoryAwareActionFeedFilter(),
        ),
    )
