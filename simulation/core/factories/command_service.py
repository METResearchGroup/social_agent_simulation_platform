"""Factory for creating the simulation command service."""

from collections.abc import Callable
from typing import Optional

from db.repositories.interfaces import (
    FeedPostRepository,
    GeneratedBioRepository,
    GeneratedFeedRepository,
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
from simulation.core.models.agents import SocialMediaAgent
from simulation.core.factories.action_history_store import (
    create_default_action_history_store_factory,
)


def create_command_service(
    *,
    run_repo: RunRepository,
    profile_repo: ProfileRepository,
    feed_post_repo: FeedPostRepository,
    generated_bio_repo: GeneratedBioRepository,
    generated_feed_repo: GeneratedFeedRepository,
    agent_factory: Callable[[int], list[SocialMediaAgent]],
    action_history_store_factory: Optional[Callable[[], ActionHistoryStore]] = None,
    feed_generator: Optional[FeedGenerator] = None,
    agent_action_rules_validator: Optional[AgentActionRulesValidator] = None,
    agent_action_history_recorder: Optional[AgentActionHistoryRecorder] = None,
    agent_action_feed_filter: Optional[AgentActionFeedFilter] = None,
) -> SimulationCommandService:
    """Create command-side service with execution dependencies."""
    if action_history_store_factory is None:
        action_history_store_factory = create_default_action_history_store_factory()
    if feed_generator is None:
        feed_generator = FeedGeneratorAdapter(
            generated_feed_repo=generated_feed_repo,
            feed_post_repo=feed_post_repo,
        )

    return SimulationCommandService(
        run_repo=run_repo,
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
