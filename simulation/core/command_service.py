import logging
import time
from collections.abc import Callable

from db.exceptions import (
    DuplicateTurnMetadataError,
    RunNotFoundError,
    RunStatusUpdateError,
)
from db.repositories.feed_post_repository import FeedPostRepository
from db.repositories.generated_bio_repository import GeneratedBioRepository
from db.repositories.generated_feed_repository import GeneratedFeedRepository
from db.repositories.profile_repository import ProfileRepository
from db.repositories.run_repository import RunRepository
from lib.utils import get_current_timestamp
from simulation.core.exceptions import InsufficientAgentsError
from simulation.core.models.actions import TurnAction
from simulation.core.models.agents import SocialMediaAgent
from simulation.core.models.posts import BlueskyFeedPost
from simulation.core.models.runs import Run, RunConfig, RunStatus
from simulation.core.models.turns import TurnMetadata, TurnResult

logger = logging.getLogger(__name__)


class SimulationCommandService:
    """Command-side service for simulation execution and state changes."""

    def __init__(
        self,
        run_repo: RunRepository,
        profile_repo: ProfileRepository,
        feed_post_repo: FeedPostRepository,
        generated_bio_repo: GeneratedBioRepository,
        generated_feed_repo: GeneratedFeedRepository,
        agent_factory: Callable[[int], list[SocialMediaAgent]],
    ):
        self.run_repo = run_repo
        self.profile_repo = profile_repo
        self.feed_post_repo = feed_post_repo
        self.generated_bio_repo = generated_bio_repo
        self.generated_feed_repo = generated_feed_repo
        self.agent_factory = agent_factory

    def execute_run(self, run_config: RunConfig) -> Run:
        """Execute a simulation run."""
        try:
            run: Run = self.run_repo.create_run(run_config)
            self.update_run_status(run, RunStatus.RUNNING)
            agents = self.create_agents_for_run(run=run, run_config=run_config)
            self.simulate_turns(
                total_turns=run.total_turns,
                run=run,
                run_config=run_config,
                agents=agents,
            )
            self.update_run_status(run, RunStatus.COMPLETED)
            return run
        except Exception:
            self.update_run_status(run, RunStatus.FAILED)
            raise

    def update_run_status(self, run: Run, status: RunStatus) -> None:
        try:
            attempts = 3
            for attempt in range(attempts):
                try:
                    self.run_repo.update_run_status(run.run_id, status)
                    break
                except RunStatusUpdateError as e:
                    if attempt == attempts - 1:
                        if status != RunStatus.FAILED:
                            try:
                                self.run_repo.update_run_status(
                                    run.run_id, RunStatus.FAILED
                                )
                            except Exception:
                                logger.warning(
                                    "Failed to update run %s status to %s",
                                    run.run_id,
                                    RunStatus.FAILED,
                                    exc_info=True,
                                )
                        raise RunStatusUpdateError(
                            run.run_id,
                            f"Failed to update status to {status.value} after 3 attempts",
                        ) from e
                    time.sleep(2**attempt)
        except Exception:
            raise

    def simulate_turn(
        self,
        run: Run,
        run_config: RunConfig,
        turn_number: int,
        agents: list[SocialMediaAgent],
    ) -> None:
        try:
            logger.info("Starting turn %d for run %s", turn_number, run.run_id)
            self._simulate_turn(
                run.run_id,
                turn_number,
                agents,
                run_config.feed_algorithm,
            )
        except Exception as e:
            logger.error(
                "Turn %d failed for run %s: %s",
                turn_number,
                run.run_id,
                e,
                exc_info=True,
                extra={
                    "run_id": run.run_id,
                    "turn_number": turn_number,
                    "num_agents": len(agents),
                    "total_turns": run.total_turns,
                },
            )
            self.update_run_status(run, RunStatus.FAILED)
            raise RuntimeError(
                f"Failed to complete turn {turn_number} for run {run.run_id}: {e}"
            ) from e

    def simulate_turns(
        self,
        total_turns: int,
        run: Run,
        run_config: RunConfig,
        agents: list[SocialMediaAgent],
    ) -> None:
        for turn_number in range(total_turns):
            self.simulate_turn(
                run=run,
                run_config=run_config,
                turn_number=turn_number,
                agents=agents,
            )

    def create_agents_for_run(
        self,
        run: Run,
        run_config: RunConfig,
    ) -> list[SocialMediaAgent]:
        try:
            agents: list[SocialMediaAgent] = self._create_agents_for_run(
                run_config, run.run_id
            )
            return agents
        except Exception:
            self.update_run_status(run, RunStatus.FAILED)
            raise

    def _simulate_turn(
        self,
        run_id: str,
        turn_number: int,
        agents: list[SocialMediaAgent],
        feed_algorithm: str,
    ) -> TurnResult:
        """Simulate a single turn of the simulation."""
        start_time = time.time()

        run = self.run_repo.get_run(run_id)
        if run is None:
            raise RunNotFoundError(run_id)

        # Lazy import keeps query/engine test modules isolated from feed stack imports.
        from feeds.feed_generator import generate_feeds

        agent_to_hydrated_feeds: dict[str, list[BlueskyFeedPost]] = generate_feeds(
            agents=agents,
            run_id=run_id,
            turn_number=turn_number,
            generated_feed_repo=self.generated_feed_repo,
            feed_post_repo=self.feed_post_repo,
            feed_algorithm=feed_algorithm,
        )

        empty_feed_count = 0
        for agent in agents:
            feed = agent_to_hydrated_feeds.get(agent.handle, [])
            if not feed:
                empty_feed_count += 1
                logger.warning(
                    f"Empty feed for agent {agent.handle} in run {run_id}, turn {turn_number}"
                )

        if agents and (empty_feed_count / len(agents)) > 0.25:
            logger.warning(
                f"Systemic issue: {empty_feed_count}/{len(agents)} feeds are empty "
                f"for run {run_id}, turn {turn_number}"
            )

        total_actions: dict[str, int] = {
            "likes": 0,
            "comments": 0,
            "follows": 0,
        }

        for agent in agents:
            feed = agent_to_hydrated_feeds.get(agent.handle, [])

            if not feed:
                continue

            likes = agent.like_posts(feed)
            comments = agent.comment_posts(feed)
            follows = agent.follow_users(feed)

            liked_uris = {like.like.post_id for like in likes}
            if len(liked_uris) != len(likes):
                seen_uris = set()
                duplicates = []
                for like in likes:
                    post_id = like.like.post_id
                    if post_id in seen_uris:
                        duplicates.append(post_id)
                    seen_uris.add(post_id)
                raise ValueError(
                    f"Agent {agent.handle} liked the same post multiple times "
                    f"in run {run_id}, turn {turn_number}. Duplicate post URIs: {duplicates}"
                )

            total_actions["likes"] += len(likes)
            total_actions["comments"] += len(comments)
            total_actions["follows"] += len(follows)

        converted_actions = self._convert_action_counts_to_enum(total_actions)
        execution_time_ms = int((time.time() - start_time) * 1000)

        turn_metadata = TurnMetadata(
            run_id=run_id,
            turn_number=turn_number,
            total_actions=converted_actions,
            created_at=get_current_timestamp(),
        )

        try:
            self.run_repo.write_turn_metadata(turn_metadata)
        except DuplicateTurnMetadataError as e:
            logger.warning(
                f"Turn metadata already exists for run {run_id}, turn {turn_number}. "
                f"This may indicate a retry or duplicate execution. Error: {e}"
            )

        return TurnResult(
            turn_number=turn_number,
            total_actions=converted_actions,
            execution_time_ms=execution_time_ms,
        )

    def _create_agents_for_run(
        self, config: RunConfig, run_id: str | None = None
    ) -> list[SocialMediaAgent]:
        """Create agents for a simulation run."""
        agents = self.agent_factory(config.num_agents)

        if len(agents) < config.num_agents:
            raise InsufficientAgentsError(
                requested=config.num_agents,
                available=len(agents),
                run_id=run_id,
            )

        handles = [agent.handle for agent in agents]
        if len(handles) != len(set(handles)):
            duplicates = [h for h in handles if handles.count(h) > 1]
            raise ValueError(
                f"Duplicate agent handles found: {set(duplicates)}. "
                "All agent handles must be unique."
            )

        logger.info(
            "Created %d agents (requested: %d) for run %s",
            len(agents),
            config.num_agents,
            run_id or "(no run_id)",
        )

        return agents

    def _convert_action_counts_to_enum(
        self, action_counts: dict[str, int]
    ) -> dict[TurnAction, int]:
        """Convert action counts from string keys to TurnAction enum keys."""
        converted: dict[TurnAction, int] = {}

        mapping = {
            "likes": TurnAction.LIKE,
            "comments": TurnAction.COMMENT,
            "follows": TurnAction.FOLLOW,
        }

        all_enum_values = set(TurnAction)
        mapped_values = set(mapping.values())
        if all_enum_values != mapped_values:
            missing = all_enum_values - mapped_values
            raise ValueError(
                f"Missing mapping for TurnAction enum values: {missing}. "
                "All enum values must be mapped."
            )

        for key, count in action_counts.items():
            if key not in mapping:
                raise ValueError(f"Unknown action type: {key}")
            converted[mapping[key]] = count

        return converted
