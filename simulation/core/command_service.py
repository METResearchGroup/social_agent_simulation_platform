import logging
import time
from collections.abc import Callable

from db.exceptions import DuplicateTurnMetadataError, RunStatusUpdateError
from db.repositories.feed_post_repository import FeedPostRepository
from db.repositories.generated_bio_repository import GeneratedBioRepository
from db.repositories.generated_feed_repository import GeneratedFeedRepository
from db.repositories.profile_repository import ProfileRepository
from db.repositories.run_repository import RunRepository
from lib.decorators import record_runtime
from lib.utils import get_current_timestamp
from simulation.core.action_history import ActionHistoryStore
from simulation.core.agent_action_feed_filter import (
    AgentActionFeedFilter,
    HistoryAwareActionFeedFilter,
)
from simulation.core.agent_action_history_recorder import AgentActionHistoryRecorder
from simulation.core.agent_action_rules_validator import AgentActionRulesValidator
from simulation.core.models.actions import TurnAction
from simulation.core.models.agents import SocialMediaAgent
from simulation.core.models.posts import BlueskyFeedPost
from simulation.core.models.runs import Run, RunConfig, RunStatus
from simulation.core.models.turns import TurnMetadata, TurnResult
from simulation.core.validators import (
    validate_agents,
    validate_agents_without_feeds,
    validate_run,
)

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
        action_history_store_factory: Callable[[], ActionHistoryStore],
        agent_action_rules_validator: AgentActionRulesValidator | None = None,
        agent_action_history_recorder: AgentActionHistoryRecorder | None = None,
        agent_action_feed_filter: AgentActionFeedFilter | None = None,
    ):
        self.run_repo = run_repo
        self.profile_repo = profile_repo
        self.feed_post_repo = feed_post_repo
        self.generated_bio_repo = generated_bio_repo
        self.generated_feed_repo = generated_feed_repo
        self.agent_factory = agent_factory
        self.action_history_store_factory = action_history_store_factory
        self.agent_action_rules_validator = (
            agent_action_rules_validator or AgentActionRulesValidator()
        )
        self.agent_action_history_recorder = (
            agent_action_history_recorder or AgentActionHistoryRecorder()
        )
        self.agent_action_feed_filter = (
            agent_action_feed_filter or HistoryAwareActionFeedFilter()
        )

    def execute_run(self, run_config: RunConfig) -> Run:
        """Execute a simulation run."""
        try:
            run: Run = self.run_repo.create_run(run_config)
            self.update_run_status(run, RunStatus.RUNNING)
            agents = self.create_agents_for_run(run=run, run_config=run_config)
            action_history_store = self.action_history_store_factory()

            self.simulate_turns(
                total_turns=run.total_turns,
                run=run,
                run_config=run_config,
                agents=agents,
                action_history_store=action_history_store,
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
        action_history_store: ActionHistoryStore,
    ) -> None:
        try:
            logger.info("Starting turn %d for run %s", turn_number, run.run_id)
            self._simulate_turn(
                run.run_id,
                turn_number,
                agents,
                run_config.feed_algorithm,
                action_history_store=action_history_store
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
        action_history_store: ActionHistoryStore,
    ) -> None:
        for turn_number in range(total_turns):
            self.simulate_turn(
                run=run,
                run_config=run_config,
                turn_number=turn_number,
                agents=agents,
                action_history_store=action_history_store,
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

    @record_runtime
    def _simulate_turn(
        self,
        run_id: str,
        turn_number: int,
        agents: list[SocialMediaAgent],
        feed_algorithm: str,
        action_history_store: ActionHistoryStore,
    ) -> TurnResult:
        """Simulate a single turn of the simulation."""

        run = self.run_repo.get_run(run_id)
        validate_run(run=run, run_id=run_id)

        from feeds.feed_generator import generate_feeds

        # TODO: revisit how feeds are generated, to make sure it's cleaned up.
        agent_to_hydrated_feeds: dict[str, list[BlueskyFeedPost]] = generate_feeds(
            agents=agents,
            run_id=run_id,
            turn_number=turn_number,
            generated_feed_repo=self.generated_feed_repo,
            feed_post_repo=self.feed_post_repo,
            feed_algorithm=feed_algorithm,
        )

        validate_agents_without_feeds(
            agent_handles=set(agent.handle for agent in agents),
            agents_with_feeds=set(agent_to_hydrated_feeds.keys()),
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

            # Filter the feed into action-specific eligible candidates. For
            # example, we don't want to allow an agent to like a post they've
            # already liked, or comment on a post they've already commented on.
            action_candidates = self.agent_action_feed_filter.filter_candidates(
                run_id=run_id,
                agent_handle=agent.handle,
                feed=feed,
                action_history_store=action_history_store,
            )

            # Generate the actions.
            likes = agent.like_posts(action_candidates.like_candidates)
            comments = agent.comment_posts(action_candidates.comment_candidates)
            follows = agent.follow_users(action_candidates.follow_candidates)

            # Validate the action rules.
            like_post_ids, comment_post_ids, follow_user_ids = (
                self.agent_action_rules_validator.validate(
                    run_id=run_id,
                    turn_number=turn_number,
                    agent_handle=agent.handle,
                    likes=likes,
                    comments=comments,
                    follows=follows,
                    action_history_store=action_history_store,
                )
            )

            # Record the action targets into the DB.
            self.agent_action_history_recorder.record(
                run_id=run_id,
                agent_handle=agent.handle,
                like_post_ids=like_post_ids,
                comment_post_ids=comment_post_ids,
                follow_user_ids=follow_user_ids,
                action_history_store=action_history_store,
            )

            total_actions["likes"] += len(likes)
            total_actions["comments"] += len(comments)
            total_actions["follows"] += len(follows)

        converted_actions = self._convert_action_counts_to_enum(total_actions)

        turn_metadata = TurnMetadata(
            run_id=run_id,
            turn_number=turn_number,
            total_actions=converted_actions,
            created_at=get_current_timestamp(),
        )

        # TODO: DuplicateMetadataError should be caught within the write_turn_metadata,
        # no need for try/except here.
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
            execution_time_ms=None,
        )

    def _create_agents_for_run(
        self, config: RunConfig, run_id: str
    ) -> list[SocialMediaAgent]:
        """Create agents for a simulation run."""
        agents = self.agent_factory(config.num_agents)
        validate_agents(agents=agents, config=config, run_id=run_id)

        # TODO: this log should live within agent_factory.
        logger.info(
            "Created %d agents (requested: %d) for run %s",
            len(agents),
            config.num_agents,
            run_id,
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
