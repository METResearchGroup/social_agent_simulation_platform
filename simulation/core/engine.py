from collections.abc import Callable, Iterable

from db.repositories.interfaces import (
    FeedPostRepository,
    GeneratedBioRepository,
    GeneratedFeedRepository,
    MetricsRepository,
    ProfileRepository,
    RunRepository,
)
from simulation.core.action_history import (
    ActionHistoryStore,
)
from simulation.core.command_service import SimulationCommandService
from simulation.core.metrics.defaults import (
    get_default_metric_keys,
    resolve_metric_keys_by_scope,
)
from simulation.core.models.agents import SocialMediaAgent
from simulation.core.models.feeds import GeneratedFeed
from simulation.core.models.metrics import RunMetrics, TurnMetrics
from simulation.core.models.posts import Post
from simulation.core.models.runs import Run, RunConfig, RunStatus
from simulation.core.models.turns import TurnData, TurnMetadata
from simulation.core.query_service import SimulationQueryService


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
        generated_bio_repo: GeneratedBioRepository,
        generated_feed_repo: GeneratedFeedRepository,
        agent_factory: Callable[[int], list[SocialMediaAgent]],
        action_history_store_factory: Callable[[], ActionHistoryStore],
        query_service: SimulationQueryService,
        command_service: SimulationCommandService,
    ):
        self.run_repo = run_repo
        self.metrics_repo = metrics_repo
        self.profile_repo = profile_repo
        self.feed_post_repo = feed_post_repo
        self.generated_bio_repo = generated_bio_repo
        self.generated_feed_repo = generated_feed_repo
        self.agent_factory = agent_factory
        self.action_history_store_factory = action_history_store_factory
        self.query_service = query_service
        self.command_service = command_service

    def execute_run(self, run_config: RunConfig) -> Run:
        return self.command_service.execute_run(run_config)

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

    def get_turn_data(self, run_id: str, turn_number: int) -> TurnData | None:
        return self.query_service.get_turn_data(run_id, turn_number)

    def read_feeds_for_turn(self, run_id: str, turn_number: int) -> list[GeneratedFeed]:
        return self.generated_feed_repo.read_feeds_for_turn(run_id, turn_number)

    def read_all_feed_posts(self) -> list[Post]:
        return self.feed_post_repo.list_all_feed_posts()

    def read_feed_posts_by_ids(self, post_ids: Iterable[str]) -> list[Post]:
        return self.feed_post_repo.read_feed_posts_by_ids(post_ids)

    def update_run_status(self, run: Run, status: RunStatus) -> None:
        self.command_service.update_run_status(run, status)

    def simulate_turn(
        self,
        run: Run,
        run_config: RunConfig,
        turn_number: int,
        agents: list[SocialMediaAgent],
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
        agents: list[SocialMediaAgent],
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
    ) -> list[SocialMediaAgent]:
        return self.command_service.create_agents_for_run(run, run_config)
