from collections.abc import Callable, Iterable

from db.repositories.interfaces import (
    AgentBioRepository,
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
from simulation.core.action_history import (
    ActionHistoryStore,
)
from simulation.core.metrics.defaults import (
    get_default_metric_keys,
    resolve_metric_keys_by_scope,
)
from simulation.core.models.agents import SimulationAgent
from simulation.core.models.feeds import GeneratedFeed
from simulation.core.models.metrics import RunMetrics, TurnMetrics
from simulation.core.models.posts import Post
from simulation.core.models.run_agents import RunAgentSnapshot
from simulation.core.models.run_follow_edges import RunFollowEdgeSnapshot
from simulation.core.models.runs import Run, RunConfig, RunStatus
from simulation.core.models.turns import TurnData, TurnMetadata
from simulation.core.services.command_service import SimulationCommandService
from simulation.core.services.query_service import SimulationQueryService
from simulation.core.utils.feed_visible_post_hydration import (
    hydrate_feed_visible_posts_for_run,
    ordered_posts_from_hydration,
)


def _get_turn_keys(run_config: RunConfig) -> list[str]:
    """Resolve metric keys from run config and return turn-scoped keys."""
    config_metric_keys = getattr(run_config, "metric_keys", None)
    metric_keys: list[str] = (
        config_metric_keys
        if config_metric_keys and len(config_metric_keys) > 0
        else get_default_metric_keys()
    )
    turn_keys, _ = resolve_metric_keys_by_scope(metric_keys)
    return turn_keys


class SimulationEngine:
    """Central orchestration layer for simulation execution."""

    def __init__(
        self,
        run_repo: RunRepository,
        metrics_repo: MetricsRepository,
        profile_repo: ProfileRepository,
        feed_post_repo: FeedPostRepository,
        generated_feed_repo: GeneratedFeedRepository,
        agent_repo: AgentRepository,
        agent_bio_repo: AgentBioRepository,
        user_agent_profile_metadata_repo: UserAgentProfileMetadataRepository,
        run_agent_repo: RunAgentRepository,
        run_follow_edge_repo: RunFollowEdgeRepository,
        run_post_repo: RunPostRepository,
        turn_post_repo: TurnPostRepository,
        run_post_like_repo: RunPostLikeRepository,
        run_post_comment_repo: RunPostCommentRepository,
        agent_factory: Callable[[int], list[SimulationAgent]],
        action_history_store_factory: Callable[[], ActionHistoryStore],
        query_service: SimulationQueryService,
        command_service: SimulationCommandService,
    ):
        self.run_repo = run_repo
        self.metrics_repo = metrics_repo
        self.profile_repo = profile_repo
        self.feed_post_repo = feed_post_repo
        self.run_post_repo = run_post_repo
        self.turn_post_repo = turn_post_repo
        self.generated_feed_repo = generated_feed_repo
        self.agent_repo = agent_repo
        self.agent_bio_repo = agent_bio_repo
        self.user_agent_profile_metadata_repo = user_agent_profile_metadata_repo
        self.run_agent_repo = run_agent_repo
        self.run_follow_edge_repo = run_follow_edge_repo
        self.agent_factory = agent_factory
        self.action_history_store_factory = action_history_store_factory
        self.run_post_like_repo = run_post_like_repo
        self.run_post_comment_repo = run_post_comment_repo
        self.query_service = query_service
        self.command_service = command_service

    def execute_run(
        self, run_config: RunConfig, created_by_app_user_id: str | None = None
    ) -> Run:
        return self.command_service.execute_run(
            run_config, created_by_app_user_id=created_by_app_user_id
        )

    def delete_run(self, run_id: str) -> None:
        """Remove a persisted run and all dependent rows."""
        self.run_repo.delete_run(run_id)

    def get_run(self, run_id: str) -> Run | None:
        return self.query_service.get_run(run_id)

    def list_runs(self) -> list[Run]:
        return self.query_service.list_runs()

    def get_turn_metadata(self, run_id: str, turn_number: int) -> TurnMetadata | None:
        return self.query_service.get_turn_metadata(run_id, turn_number)

    def list_turn_metadata(self, run_id: str) -> list[TurnMetadata]:
        return self.query_service.list_turn_metadata(run_id)

    def get_turn_metrics(self, run_id: str, turn_number: int) -> TurnMetrics | None:
        return self.query_service.get_turn_metrics(run_id, turn_number)

    def list_turn_metrics(self, run_id: str) -> list[TurnMetrics]:
        return self.query_service.list_turn_metrics(run_id)

    def get_run_metrics(self, run_id: str) -> RunMetrics | None:
        return self.query_service.get_run_metrics(run_id)

    def list_run_follow_edges(self, run_id: str) -> list[RunFollowEdgeSnapshot]:
        return self.query_service.list_run_follow_edges(run_id)

    def list_run_agents(self, run_id: str) -> list[RunAgentSnapshot]:
        return self.query_service.list_run_agents(run_id)

    def get_turn_data(self, run_id: str, turn_number: int) -> TurnData | None:
        return self.query_service.get_turn_data(run_id, turn_number)

    def read_feeds_for_turn(self, run_id: str, turn_number: int) -> list[GeneratedFeed]:
        return self.generated_feed_repo.read_feeds_for_turn(run_id, turn_number)

    def read_all_feed_posts(self) -> list[Post]:
        return self.feed_post_repo.list_all_feed_posts()

    def read_feed_posts_by_ids(self, post_ids: Iterable[str]) -> list[Post]:
        return self.feed_post_repo.read_feed_posts_by_ids(post_ids)

    def read_posts_for_run(self, run_id: str, post_ids: Iterable[str]) -> list[Post]:
        """Resolve feed-visible post IDs to :class:`Post` via run + turn stores."""
        post_ids_list = list(post_ids)
        mapping = hydrate_feed_visible_posts_for_run(
            run_id,
            post_ids_list,
            run_post_repo=self.run_post_repo,
            turn_post_repo=self.turn_post_repo,
            run_post_like_repo=self.run_post_like_repo,
            run_post_comment_repo=self.run_post_comment_repo,
        )
        return ordered_posts_from_hydration(post_ids_list, mapping)

    def update_run_status(self, run: Run, status: RunStatus) -> None:
        self.command_service.update_run_status(run, status)

    def simulate_turn(
        self,
        run: Run,
        run_config: RunConfig,
        turn_number: int,
        agents: list[SimulationAgent],
    ) -> None:
        turn_keys = _get_turn_keys(run_config)
        self.command_service.simulate_turn(
            run,
            run_config,
            turn_number,
            agents,
            action_history_store=self.action_history_store_factory(),
            turn_metric_keys=turn_keys,
        )

    def simulate_turns(
        self,
        total_turns: int,
        run: Run,
        run_config: RunConfig,
        agents: list[SimulationAgent],
    ) -> None:
        turn_keys = _get_turn_keys(run_config)
        self.command_service.simulate_turns(
            total_turns,
            run,
            run_config,
            agents,
            action_history_store=self.action_history_store_factory(),
            turn_metric_keys=turn_keys,
        )

    def create_agents_for_run(
        self,
        run: Run,
        run_config: RunConfig,
    ) -> list[SimulationAgent]:
        return self.command_service.create_agents_for_run(run, run_config)
