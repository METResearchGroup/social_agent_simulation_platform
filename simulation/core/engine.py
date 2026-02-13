from collections.abc import Callable
from typing import Optional

from db.repositories.feed_post_repository import FeedPostRepository
from db.repositories.generated_bio_repository import GeneratedBioRepository
from db.repositories.generated_feed_repository import GeneratedFeedRepository
from db.repositories.profile_repository import ProfileRepository
from db.repositories.run_repository import RunRepository
from simulation.core.command_service import SimulationCommandService
from simulation.core.models.agents import SocialMediaAgent
from simulation.core.models.runs import Run, RunConfig, RunStatus
<<<<<<< HEAD
from simulation.core.models.turns import TurnData, TurnMetadata, TurnResult
from simulation.core.validators import validate_run_id, validate_turn_number

logger = logging.getLogger(__name__)
=======
from simulation.core.models.turns import TurnData, TurnMetadata
from simulation.core.query_service import SimulationQueryService
>>>>>>> 33f5781dcd1a2d62ca2f6fb8b32b3b0a2c9c6f4c


class SimulationEngine:
    """Backward-compatible facade over command and query services."""

    def __init__(
        self,
        run_repo: RunRepository,
        profile_repo: ProfileRepository,
        feed_post_repo: FeedPostRepository,
        generated_bio_repo: GeneratedBioRepository,
        generated_feed_repo: GeneratedFeedRepository,
        agent_factory: Callable[[int], list[SocialMediaAgent]],
        query_service: Optional[SimulationQueryService] = None,
        command_service: Optional[SimulationCommandService] = None,
    ):
        self.run_repo = run_repo
        self.profile_repo = profile_repo
        self.feed_post_repo = feed_post_repo
        self.generated_bio_repo = generated_bio_repo
        self.generated_feed_repo = generated_feed_repo
        self.agent_factory = agent_factory

        self.query_service = query_service or SimulationQueryService(
            run_repo=run_repo,
            feed_post_repo=feed_post_repo,
            generated_feed_repo=generated_feed_repo,
        )
        self.command_service = command_service or SimulationCommandService(
            run_repo=run_repo,
            profile_repo=profile_repo,
            feed_post_repo=feed_post_repo,
            generated_bio_repo=generated_bio_repo,
            generated_feed_repo=generated_feed_repo,
            agent_factory=agent_factory,
        )

    def execute_run(self, run_config: RunConfig) -> Run:
        return self.command_service.execute_run(run_config)

    def get_run(self, run_id: str) -> Optional[Run]:
        return self.query_service.get_run(run_id)

    def list_runs(self) -> list[Run]:
        return self.query_service.list_runs()

    def get_turn_metadata(
        self, run_id: str, turn_number: int
    ) -> Optional[TurnMetadata]:
        return self.query_service.get_turn_metadata(run_id, turn_number)

    def get_turn_data(self, run_id: str, turn_number: int) -> Optional[TurnData]:
        return self.query_service.get_turn_data(run_id, turn_number)

    def update_run_status(self, run: Run, status: RunStatus) -> None:
        self.command_service.update_run_status(run, status)

    def simulate_turn(
        self,
        run: Run,
        run_config: RunConfig,
        turn_number: int,
        agents: list[SocialMediaAgent],
    ) -> None:
        self.command_service.simulate_turn(run, run_config, turn_number, agents)

    def simulate_turns(
        self,
        total_turns: int,
        run: Run,
        run_config: RunConfig,
        agents: list[SocialMediaAgent],
    ) -> None:
        self.command_service.simulate_turns(total_turns, run, run_config, agents)

    def create_agents_for_run(
        self,
        run: Run,
        run_config: RunConfig,
    ) -> list[SocialMediaAgent]:
        return self.command_service.create_agents_for_run(run, run_config)
