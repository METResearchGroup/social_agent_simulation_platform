"""Factory for creating the simulation command service."""

from collections.abc import Callable

from db.repositories.interfaces import (
    FeedPostRepository,
    GeneratedBioRepository,
    GeneratedFeedRepository,
    MetricsRepository,
    ProfileRepository,
    RunRepository,
)
from feeds.feed_generator_adapter import FeedGeneratorAdapter
from feeds.interfaces import FeedGenerator
from simulation.core.action_history import ActionHistoryStore
from simulation.core.agent_action_feed_filter import (
    AgentActionFeedFilter,
    HistoryAwareActionFeedFilter,
)
from simulation.core.agent_action_history_recorder import AgentActionHistoryRecorder
from simulation.core.agent_action_rules_validator import AgentActionRulesValidator
from simulation.core.command_service import SimulationCommandService
from simulation.core.factories.action_history_store import (
    create_default_action_history_store_factory,
)
from simulation.core.metrics.collector import MetricsCollector
from simulation.core.metrics.defaults import (
    DEFAULT_RUN_METRIC_KEYS,
    DEFAULT_TURN_METRIC_KEYS,
    create_default_metrics_registry,
)
from simulation.core.metrics.interfaces import MetricDeps
from simulation.core.metrics.registry import MetricsRegistry
from simulation.core.models.agents import SocialMediaAgent


def create_command_service(
    *,
    run_repo: RunRepository,
    metrics_repo: MetricsRepository,
    profile_repo: ProfileRepository,
    feed_post_repo: FeedPostRepository,
    generated_bio_repo: GeneratedBioRepository,
    generated_feed_repo: GeneratedFeedRepository,
    agent_factory: Callable[[int], list[SocialMediaAgent]],
    action_history_store_factory: Callable[[], ActionHistoryStore] | None = None,
    feed_generator: FeedGenerator | None = None,
    metrics_collector: MetricsCollector | None = None,
    agent_action_rules_validator: AgentActionRulesValidator | None = None,
    agent_action_history_recorder: AgentActionHistoryRecorder | None = None,
    agent_action_feed_filter: AgentActionFeedFilter | None = None,
) -> SimulationCommandService:
    """Create command-side service with execution dependencies."""
    if action_history_store_factory is None:
        action_history_store_factory = create_default_action_history_store_factory()
    if feed_generator is None:
        feed_generator = FeedGeneratorAdapter(
            generated_feed_repo=generated_feed_repo,
            feed_post_repo=feed_post_repo,
        )

    if metrics_collector is None:
        registry: MetricsRegistry = create_default_metrics_registry()
        deps = MetricDeps(
            run_repo=run_repo, metrics_repo=metrics_repo, sql_executor=None
        )
        metrics_collector = MetricsCollector(
            registry=registry,
            turn_metric_keys=DEFAULT_TURN_METRIC_KEYS,
            run_metric_keys=DEFAULT_RUN_METRIC_KEYS,
            deps=deps,
        )

    return SimulationCommandService(
        run_repo=run_repo,
        metrics_repo=metrics_repo,
        metrics_collector=metrics_collector,
        profile_repo=profile_repo,
        feed_post_repo=feed_post_repo,
        generated_bio_repo=generated_bio_repo,
        generated_feed_repo=generated_feed_repo,
        agent_factory=agent_factory,
        action_history_store_factory=action_history_store_factory,
        feed_generator=feed_generator,
        agent_action_rules_validator=agent_action_rules_validator
        or AgentActionRulesValidator(),
        agent_action_history_recorder=agent_action_history_recorder
        or AgentActionHistoryRecorder(),
        agent_action_feed_filter=agent_action_feed_filter
        or HistoryAwareActionFeedFilter(),
    )
