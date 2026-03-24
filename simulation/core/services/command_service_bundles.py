"""Dependency bundles for :class:`simulation.core.services.command_service.SimulationCommandService`.

Repository groupings follow ``docs/architecture/agents-turns-runs-data-model.md`` and related
architecture docs. Keeping them in one module avoids import cycles between the service and
``simulation.core.factories``.
"""

from collections.abc import Callable
from dataclasses import dataclass

from db.adapters.base import TransactionProvider
from db.repositories.interfaces import (
    AgentBioRepository,
    AgentFollowEdgeRepository,
    AgentPostCommentRepository,
    AgentPostLikeRepository,
    AgentPostRepository,
    AgentRepository,
    FeedPostRepository,
    GeneratedFeedRepository,
    MetricsRepository,
    ProfileRepository,
    RunAgentRepository,
    RunFollowEdgeRepository,
    RunPostCommentRepository,
    RunPostLikeRepository,
    RunPostRepository,
    RunRepository,
    TurnPostRepository,
    UserAgentProfileMetadataRepository,
)
from feeds.interfaces import FeedGenerator
from simulation.core.action_history import ActionHistoryStore
from simulation.core.action_policy import (
    AgentActionFeedFilter,
    AgentActionRulesValidator,
)
from simulation.core.models.agents import SimulationAgent


@dataclass(frozen=True, slots=True)
class AgentRepos:
    """Seed-state (`Agent*`) repositories: editable catalog before any run.

    See ``docs/architecture/agents-turns-runs-data-model.md`` and
    ``docs/architecture/seed-state-run-snapshot-turn-events.md``.
    """

    agent_repo: AgentRepository
    agent_bio_repo: AgentBioRepository
    agent_follow_edge_repo: AgentFollowEdgeRepository
    user_agent_profile_metadata_repo: UserAgentProfileMetadataRepository
    agent_post_repo: AgentPostRepository
    agent_post_like_repo: AgentPostLikeRepository
    agent_post_comment_repo: AgentPostCommentRepository


@dataclass(frozen=True, slots=True)
class RunRepos:
    """Run identity, run-start snapshot tables, and run-level derived summaries.

    Covers ``runs``, ``run_*`` snapshot stores, and run-scope metrics (e.g.
    ``run_metrics``). See ``docs/architecture/run-snapshots.md``.
    """

    run_repo: RunRepository
    metrics_repo: MetricsRepository
    run_agent_repo: RunAgentRepository
    run_follow_edge_repo: RunFollowEdgeRepository
    run_post_repo: RunPostRepository
    run_post_like_repo: RunPostLikeRepository
    run_post_comment_repo: RunPostCommentRepository


@dataclass(frozen=True, slots=True)
class TurnRepos:
    """Per-turn outputs (append-only history during a run).

    Today this is mainly generated feeds; other turn-event stores (e.g. metrics
    wired elsewhere) may be grouped here as the command surface grows. See
    ``docs/architecture/seed-state-run-snapshot-turn-events.md``.
    """

    generated_feed_repo: GeneratedFeedRepository
    turn_post_repo: TurnPostRepository


@dataclass(frozen=True, slots=True)
class CommandServiceRepos:
    """Wiring for command-side simulation execution.

    Composes scope-specific repository bundles plus supporting repositories that
    are not Agent*/Run*/Turn* lifecycle tables (e.g. ingest/legacy substrate) and
    transaction scope.
    """

    agent: AgentRepos
    run: RunRepos
    turn: TurnRepos
    profile_repo: ProfileRepository
    feed_post_repo: FeedPostRepository
    transaction_provider: TransactionProvider


@dataclass(frozen=True, slots=True)
class CommandServiceRuntime:
    """Non-repository collaborators for simulation command execution."""

    agent_factory: Callable[[int], list[SimulationAgent]]
    action_history_store_factory: Callable[[], ActionHistoryStore]
    feed_generator: FeedGenerator
    agent_action_rules_validator: AgentActionRulesValidator
    agent_action_feed_filter: AgentActionFeedFilter
