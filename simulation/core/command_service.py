import logging
from collections.abc import Mapping
from uuid import uuid4

from pydantic import JsonValue

from db.services.simulation_persistence_service import SimulationPersistenceService
from lib.decorators import timed
from lib.timestamp_utils import get_current_timestamp
from simulation.core.action_history import ActionHistoryStore, record_action_targets
from simulation.core.agent_actions import (
    generate_comments,
    generate_follows,
    generate_likes,
)
from simulation.core.command_service_bundles import (
    CommandServiceRepos,
    CommandServiceRuntime,
)
from simulation.core.metrics.collector import MetricsCollector
from simulation.core.metrics.defaults import (
    resolve_metric_keys_by_scope,
)
from simulation.core.models.actions import TurnAction
from simulation.core.models.agents import SimulationAgent
from simulation.core.models.generated.comment import GeneratedComment
from simulation.core.models.generated.follow import GeneratedFollow
from simulation.core.models.generated.like import GeneratedLike
from simulation.core.models.metrics import ComputedMetrics, RunMetrics, TurnMetrics
from simulation.core.models.posts import Post
from simulation.core.models.run_agents import RunAgentSnapshot
from simulation.core.models.run_follow_edges import RunFollowEdgeSnapshot
from simulation.core.models.run_post_likes import RunPostLikeSnapshot
from simulation.core.models.run_posts import RunPostSnapshot
from simulation.core.models.runs import Run, RunConfig, RunStatus
from simulation.core.models.turns import TurnMetadata, TurnResult
from simulation.core.seed_state import hydrate_seed_state
from simulation.core.utils.exceptions import RunStatusUpdateError, SimulationRunFailure
from simulation.core.utils.retry import retry_with_exponential_backoff
from simulation.core.utils.validators import (
    validate_agents_without_feeds,
    validate_duplicate_agent_handles,
    validate_insufficient_agents,
    validate_run_exists,
)

logger = logging.getLogger(__name__)

STATUS_UPDATE_MAX_ATTEMPTS: int = 3
STATUS_UPDATE_BACKOFF_BASE: int = 2


class SimulationCommandService:
    """Command-side service for simulation execution and state changes."""

    def __init__(
        self,
        *,
        repos: CommandServiceRepos,
        metrics_collector: MetricsCollector,
        simulation_persistence: SimulationPersistenceService,
        runtime: CommandServiceRuntime,
    ) -> None:
        self.run_repo = repos.run.run_repo
        self.metrics_repo = repos.run.metrics_repo
        self.metrics_collector = metrics_collector
        self.simulation_persistence = simulation_persistence
        self.profile_repo = repos.profile_repo
        self.feed_post_repo = repos.feed_post_repo
        self.generated_feed_repo = repos.turn.generated_feed_repo
        self.agent_repo = repos.agent.agent_repo
        self.agent_bio_repo = repos.agent.agent_bio_repo
        self.agent_follow_edge_repo = repos.agent.agent_follow_edge_repo
        self.user_agent_profile_metadata_repo = (
            repos.agent.user_agent_profile_metadata_repo
        )
        self.run_agent_repo = repos.run.run_agent_repo
        self.run_follow_edge_repo = repos.run.run_follow_edge_repo
        self.run_post_repo = repos.run.run_post_repo
        self.run_post_like_repo = repos.run.run_post_like_repo
        self.agent_post_repo = repos.agent.agent_post_repo
        self.agent_post_like_repo = repos.agent.agent_post_like_repo
        self.transaction_provider = repos.transaction_provider
        self.agent_factory = runtime.agent_factory
        self.action_history_store_factory = runtime.action_history_store_factory
        self.feed_generator = runtime.feed_generator
        self.agent_action_rules_validator = runtime.agent_action_rules_validator
        self.agent_action_feed_filter = runtime.agent_action_feed_filter

    def execute_run(
        self, run_config: RunConfig, created_by_app_user_id: str | None = None
    ) -> Run:
        """Execute a simulation run."""
        try:
            run = self.run_repo.create_run(
                run_config, created_by_app_user_id=created_by_app_user_id
            )
            self.update_run_status(run, RunStatus.RUNNING)
        except Exception as e:
            raise SimulationRunFailure(
                message="Run creation or status update failed",
                run_id=None,
                cause=e,
            ) from e

        try:
            agents = self.create_agents_for_run(run=run, run_config=run_config)
            (
                run_agent_snapshots,
                run_follow_edge_snapshots,
                run_post_like_snapshots,
            ) = self.snapshot_run_initial_state(run=run, agents=agents)
            action_history_store = self.action_history_store_factory()
            self.preload_follow_history_from_snapshots(
                run_id=run.run_id,
                run_agent_snapshots=run_agent_snapshots,
                run_follow_edge_snapshots=run_follow_edge_snapshots,
                action_history_store=action_history_store,
            )
            self.preload_like_history_from_snapshots(
                run_id=run.run_id,
                run_agent_snapshots=run_agent_snapshots,
                run_post_like_snapshots=run_post_like_snapshots,
                action_history_store=action_history_store,
            )

            turn_keys, run_keys = resolve_metric_keys_by_scope(run.metric_keys)
            self.simulate_turns(
                total_turns=run.total_turns,
                run=run,
                run_config=run_config,
                agents=agents,
                action_history_store=action_history_store,
                turn_metric_keys=turn_keys,
            )
            run_metrics_dict: ComputedMetrics = (
                self.metrics_collector.collect_run_metrics(
                    run_id=run.run_id,
                    run_metric_keys=run_keys,
                )
            )
            run_metrics = RunMetrics(
                run_id=run.run_id,
                metrics=run_metrics_dict,
                created_at=get_current_timestamp(),
            )
            self.simulation_persistence.write_run(run.run_id, run_metrics)
            return run
        except Exception as e:
            self.update_run_status(run, RunStatus.FAILED)
            raise SimulationRunFailure(
                message="Run failed during execution",
                run_id=run.run_id,
                cause=e,
            ) from e

    def snapshot_run_initial_state(
        self,
        *,
        run: Run,
        agents: list[SimulationAgent],
    ) -> tuple[
        list[RunAgentSnapshot],
        list[RunFollowEdgeSnapshot],
        list[RunPostLikeSnapshot],
    ]:
        """Persist run-start agent/follow-edge/post snapshots in one transaction."""
        with self.transaction_provider.run_transaction() as conn:
            run_agent_snapshots = self.snapshot_run_agents(
                run=run,
                agents=agents,
                conn=conn,
            )
            run_follow_edge_snapshots = self.snapshot_run_follow_edges(
                run=run,
                agent_snapshots=run_agent_snapshots,
                conn=conn,
            )
            run_post_snapshots = self.snapshot_run_posts(
                run=run,
                run_agent_snapshots=run_agent_snapshots,
                conn=conn,
            )
            run_post_like_snapshots = self.snapshot_run_post_likes(
                run=run,
                run_agent_snapshots=run_agent_snapshots,
                run_post_snapshots=run_post_snapshots,
                conn=conn,
            )
        return (
            run_agent_snapshots,
            run_follow_edge_snapshots,
            run_post_like_snapshots,
        )

    def update_run_status(
        self,
        run: Run,
        status: RunStatus,
    ) -> None:
        """Update run status, retrying transient DB errors with backoff."""

        def _attempt_update() -> None:
            self.run_repo.update_run_status(run.run_id, status)

        try:
            retry_with_exponential_backoff(
                operation=_attempt_update,
                retry_on=RunStatusUpdateError,
                max_attempts=STATUS_UPDATE_MAX_ATTEMPTS,
                backoff_base=STATUS_UPDATE_BACKOFF_BASE,
            )
        except RunStatusUpdateError as e:
            # Best-effort: if the requested status isn't terminal, attempt to
            # mark the run as FAILED on final retry exhaustion.
            if status != RunStatus.FAILED:
                try:
                    self.run_repo.update_run_status(run.run_id, RunStatus.FAILED)
                except Exception:
                    logger.warning(
                        "Failed to update run %s status to %s",
                        run.run_id,
                        RunStatus.FAILED,
                        exc_info=True,
                    )

            raise RunStatusUpdateError(
                run.run_id,
                (
                    "Failed to update status to "
                    f"{status.value} after {STATUS_UPDATE_MAX_ATTEMPTS} attempts"
                ),
            ) from e

    def simulate_turn(
        self,
        run: Run,
        run_config: RunConfig,
        turn_number: int,
        agents: list[SimulationAgent],
        action_history_store: ActionHistoryStore,
        turn_metric_keys: list[str],
    ) -> None:
        try:
            logger.info("Starting turn %d for run %s", turn_number, run.run_id)
            feed_algorithm_config: Mapping[str, JsonValue] | None = (
                run_config.feed_algorithm_config
            )
            self._simulate_turn(
                run=run,
                turn_number=turn_number,
                agents=agents,
                feed_algorithm=run_config.feed_algorithm,
                action_history_store=action_history_store,
                turn_metric_keys=turn_metric_keys,
                feed_algorithm_config=feed_algorithm_config,
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
        agents: list[SimulationAgent],
        action_history_store: ActionHistoryStore,
        turn_metric_keys: list[str],
    ) -> None:
        validate_run_exists(run=run, run_id=run.run_id)
        for turn_number in range(total_turns):
            self.simulate_turn(
                run=run,
                run_config=run_config,
                turn_number=turn_number,
                agents=agents,
                action_history_store=action_history_store,
                turn_metric_keys=turn_metric_keys,
            )

    def create_agents_for_run(
        self,
        run: Run,
        run_config: RunConfig,
    ) -> list[SimulationAgent]:
        try:
            agents: list[SimulationAgent] = self._create_agents_for_run(
                run_config, run.run_id
            )
            return agents
        except Exception:
            self.update_run_status(run, RunStatus.FAILED)
            raise

    @timed()
    def _simulate_turn(
        self,
        run: Run,
        turn_number: int,
        agents: list[SimulationAgent],
        feed_algorithm: str,
        action_history_store: ActionHistoryStore,
        turn_metric_keys: list[str],
        feed_algorithm_config: Mapping[str, JsonValue] | None = None,
    ) -> TurnResult:
        """Simulate a single turn of the simulation."""
        run_id: str = run.run_id

        agent_to_hydrated_feeds: dict[str, list[Post]] = (
            self.feed_generator.generate_feeds(
                agents=agents,
                run_id=run_id,
                turn_number=turn_number,
                feed_algorithm=feed_algorithm,
                feed_algorithm_config=feed_algorithm_config,
            )
        )

        validate_agents_without_feeds(
            agent_handles=set(agent.handle for agent in agents),
            agents_with_feeds=set(agent_to_hydrated_feeds.keys()),
        )

        total_actions: dict[TurnAction, int] = {action: 0 for action in TurnAction}
        turn_likes: list[GeneratedLike] = []
        turn_comments: list[GeneratedComment] = []
        turn_follows: list[GeneratedFollow] = []

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
            likes = generate_likes(
                action_candidates.like_candidates,
                run_id=run_id,
                turn_number=turn_number,
                agent_handle=agent.handle,
            )
            comments = generate_comments(
                action_candidates.comment_candidates,
                run_id=run_id,
                turn_number=turn_number,
                agent_handle=agent.handle,
            )
            follows = generate_follows(
                action_candidates.follow_candidates,
                run_id=run_id,
                turn_number=turn_number,
                agent_handle=agent.handle,
            )

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

            # Record the action targets into action history.
            record_action_targets(
                run_id=run_id,
                agent_handle=agent.handle,
                like_post_ids=like_post_ids,
                comment_post_ids=comment_post_ids,
                follow_user_ids=follow_user_ids,
                action_history_store=action_history_store,
            )

            turn_likes.extend(likes)
            turn_comments.extend(comments)
            turn_follows.extend(follows)
            total_actions[TurnAction.LIKE] += len(likes)
            total_actions[TurnAction.COMMENT] += len(comments)
            total_actions[TurnAction.FOLLOW] += len(follows)

        created_at: str = get_current_timestamp()

        turn_metadata = TurnMetadata(
            run_id=run_id,
            turn_number=turn_number,
            total_actions=total_actions,
            created_at=created_at,
        )

        computed_metrics: ComputedMetrics = self.metrics_collector.collect_turn_metrics(
            run_id=run_id,
            turn_number=turn_number,
            turn_metric_keys=turn_metric_keys,
        )
        turn_metrics = TurnMetrics(
            run_id=run_id,
            turn_number=turn_number,
            metrics=computed_metrics,
            created_at=created_at,
        )

        self.simulation_persistence.write_turn(
            turn_metadata=turn_metadata,
            turn_metrics=turn_metrics,
            likes=turn_likes,
            comments=turn_comments,
            follows=turn_follows,
        )

        return TurnResult(
            turn_number=turn_number,
            total_actions=total_actions,
            execution_time_ms=None,
        )

    def _create_agents_for_run(
        self, config: RunConfig, run_id: str
    ) -> list[SimulationAgent]:
        """Create agents for a simulation run."""
        agents = self.agent_factory(config.num_agents)
        validate_insufficient_agents(
            agents=agents,
            requested_agents=config.num_agents,
        )
        validate_duplicate_agent_handles(agents=agents)

        # TODO: this log should live within agent_factory.
        logger.info(
            "Created %d agents (requested: %d) for run %s",
            len(agents),
            config.num_agents,
            run_id,
        )

        return agents

    def snapshot_run_agents(
        self,
        run: Run,
        agents: list[SimulationAgent],
        *,
        conn: object | None = None,
    ) -> list[RunAgentSnapshot]:
        """Persist the exact ordered seed-state agents selected for a run."""
        snapshots = self._try_build_run_agent_snapshots_from_agents(
            run=run, agents=agents
        )
        if snapshots is not None:
            self.run_agent_repo.write_run_agents(run.run_id, snapshots, conn=conn)
            return snapshots

        snapshots = self._build_run_agent_snapshots_from_repos(run=run, agents=agents)
        self.run_agent_repo.write_run_agents(run.run_id, snapshots, conn=conn)
        return snapshots

    def snapshot_run_follow_edges(
        self,
        run: Run,
        agent_snapshots: list[RunAgentSnapshot],
        *,
        conn: object | None = None,
    ) -> list[RunFollowEdgeSnapshot]:
        """Persist the run-start internal follow graph for the selected agents."""
        if not agent_snapshots:
            return []

        selected_agent_ids: list[str] = [
            snapshot.agent_id for snapshot in agent_snapshots
        ]
        selected_agent_id_set: set[str] = set(selected_agent_ids)
        seed_edges = self.agent_follow_edge_repo.list_edges_for_follower_agent_ids(
            selected_agent_ids,
            conn=conn,
        )

        snapshots: list[RunFollowEdgeSnapshot] = []
        for edge in seed_edges:
            if edge.target_agent_id not in selected_agent_id_set:
                continue
            snapshots.append(
                RunFollowEdgeSnapshot(
                    run_id=run.run_id,
                    follower_agent_id=edge.follower_agent_id,
                    target_agent_id=edge.target_agent_id,
                    created_at=run.created_at,
                )
            )

        self.run_follow_edge_repo.write_run_follow_edges(
            run.run_id,
            snapshots,
            conn=conn,
        )
        return snapshots

    def snapshot_run_posts(
        self,
        run: Run,
        run_agent_snapshots: list[RunAgentSnapshot],
        *,
        conn: object | None = None,
    ) -> list[RunPostSnapshot]:
        """Persist run-start post snapshots from agent_posts for selected agents."""
        if not run_agent_snapshots:
            return []

        agent_ids = [s.agent_id for s in run_agent_snapshots]
        agent_posts = self.agent_post_repo.list_posts_for_agent_ids(
            agent_ids,
            conn=conn,
        )

        handle_by_agent_id: dict[str, str] = {
            s.agent_id: s.handle_at_start for s in run_agent_snapshots
        }
        display_name_by_agent_id: dict[str, str] = {
            s.agent_id: s.display_name_at_start for s in run_agent_snapshots
        }

        snapshots: list[RunPostSnapshot] = []
        for agent_post in agent_posts:
            author_handle = handle_by_agent_id.get(agent_post.agent_id)
            author_display_name = display_name_by_agent_id.get(agent_post.agent_id)
            if author_handle is None or author_display_name is None:
                # NOTE: Currently, we constrain this so that only posts by agents in the
                # network can be used; we don't have exogenous posts right now. But this is
                # something that we'll obviously want to revisit in the future, as it is
                # likely the case that we'll want agents to see posts by agents
                # not in their social network.
                raise ValueError(
                    "Post is written by an agent that is not in the run. This is unexpected behavior."
                )
            snapshots.append(
                RunPostSnapshot(
                    run_post_id=str(uuid4()),
                    run_id=run.run_id,
                    agent_post_id=agent_post.agent_post_id,
                    author_agent_id=agent_post.agent_id,
                    author_handle_at_start=author_handle,
                    author_display_name_at_start=author_display_name,
                    body_text_at_start=agent_post.body_text,
                    published_at_start=agent_post.published_at,
                    source_post_id_at_start=agent_post.source_post_id,
                    source_at_start=agent_post.source,
                    source_uri_at_start=agent_post.source_uri,
                    created_at=run.created_at,
                )
            )

        self.run_post_repo.write_run_posts(run.run_id, snapshots, conn=conn)
        return snapshots

    def snapshot_run_post_likes(
        self,
        *,
        run: Run,
        run_agent_snapshots: list[RunAgentSnapshot],
        run_post_snapshots: list[RunPostSnapshot],
        conn: object | None = None,
    ) -> list[RunPostLikeSnapshot]:
        """Snapshot seed-state likes into `run_post_likes` at run creation time.

        Selection rule:
        - liked post exists in this run's `run_posts`
        - liker is a member of this run's `run_agents`
        """
        if not run_agent_snapshots or not run_post_snapshots:
            return []

        selected_agent_ids: set[str] = {s.agent_id for s in run_agent_snapshots}
        handle_by_agent_id: dict[str, str] = {
            s.agent_id: s.handle_at_start for s in run_agent_snapshots
        }
        display_name_by_agent_id: dict[str, str] = {
            s.agent_id: s.display_name_at_start for s in run_agent_snapshots
        }

        agent_post_id_to_run_post_id: dict[str, str] = {
            s.agent_post_id: s.run_post_id for s in run_post_snapshots
        }
        agent_post_ids = list(agent_post_id_to_run_post_id.keys())

        seed_likes = self.agent_post_like_repo.list_likes_for_agent_post_ids(
            agent_post_ids,
            conn=conn,
        )

        rows: list[RunPostLikeSnapshot] = []
        for like in seed_likes:
            if like.liker_agent_id not in selected_agent_ids:
                continue
            run_post_id = agent_post_id_to_run_post_id.get(like.agent_post_id)
            if run_post_id is None:
                continue

            liker_handle_at_start = handle_by_agent_id.get(like.liker_agent_id)
            liker_display_name_at_start = display_name_by_agent_id.get(
                like.liker_agent_id
            )
            if liker_handle_at_start is None or liker_display_name_at_start is None:
                raise ValueError(
                    "Run post like snapshot like references an agent missing from run_agents"
                )

            rows.append(
                RunPostLikeSnapshot(
                    run_post_like_id=str(uuid4()),
                    run_id=run.run_id,
                    run_post_id=run_post_id,
                    liker_agent_id=like.liker_agent_id,
                    liker_handle_at_start=liker_handle_at_start,
                    liker_display_name_at_start=liker_display_name_at_start,
                    created_at=run.created_at,
                )
            )

        self.run_post_like_repo.write_run_post_likes(
            run.run_id,
            rows,
            conn=conn,
        )
        return rows

    def preload_follow_history_from_snapshots(
        self,
        *,
        run_id: str,
        run_agent_snapshots: list[RunAgentSnapshot],
        run_follow_edge_snapshots: list[RunFollowEdgeSnapshot],
        action_history_store: ActionHistoryStore,
    ) -> None:
        """Seed follow history so duplicate-follow suppression uses the run snapshot."""
        handle_by_agent_id: dict[str, str] = {
            snapshot.agent_id: snapshot.handle_at_start
            for snapshot in run_agent_snapshots
        }
        for snapshot in run_follow_edge_snapshots:
            follower_handle = handle_by_agent_id.get(snapshot.follower_agent_id)
            target_handle = handle_by_agent_id.get(snapshot.target_agent_id)
            if follower_handle is None or target_handle is None:
                raise ValueError(
                    "Run follow edge snapshot references an agent missing from run_agents"
                )
            action_history_store.record_follow(run_id, follower_handle, target_handle)

    def preload_like_history_from_snapshots(
        self,
        *,
        run_id: str,
        run_agent_snapshots: list[RunAgentSnapshot],
        run_post_like_snapshots: list[RunPostLikeSnapshot],
        action_history_store: ActionHistoryStore,
    ) -> None:
        """Seed like history so duplicate-like suppression treats seeded likes as done."""
        handle_by_agent_id: dict[str, str] = {
            snapshot.agent_id: snapshot.handle_at_start
            for snapshot in run_agent_snapshots
        }

        for snapshot in run_post_like_snapshots:
            liker_handle = handle_by_agent_id.get(snapshot.liker_agent_id)
            if liker_handle is None:
                raise ValueError(
                    "Run post like snapshot references an agent missing from run_agents"
                )
            action_history_store.record_like(
                run_id,
                liker_handle,
                snapshot.run_post_id,
            )

    def _try_build_run_agent_snapshots_from_agents(
        self, *, run: Run, agents: list[SimulationAgent]
    ) -> list[RunAgentSnapshot] | None:
        """Return snapshots built directly from hydrated SimulationAgent objects."""
        if not agents:
            return []

        if not all(
            getattr(agent, "agent_id", None)
            and getattr(agent, "display_name", None)
            and getattr(agent, "bio", None)
            for agent in agents
        ):
            return None

        snapshots: list[RunAgentSnapshot] = []
        for selection_order, agent in enumerate(agents):
            agent_id = agent.agent_id
            display_name = agent.display_name
            if agent_id is None or display_name is None:
                raise ValueError(
                    "Invariant violation: hydrated agent missing identifier fields"
                )

            snapshots.append(
                RunAgentSnapshot(
                    run_id=run.run_id,
                    agent_id=agent_id,
                    selection_order=selection_order,
                    handle_at_start=agent.handle,
                    display_name_at_start=display_name,
                    persona_bio_at_start=agent.bio,
                    followers_count_at_start=agent.followers,
                    follows_count_at_start=agent.following,
                    posts_count_at_start=agent.posts_count,
                    created_at=run.created_at,
                )
            )

        return snapshots

    def _build_run_agent_snapshots_from_repos(
        self, *, run: Run, agents: list[SimulationAgent]
    ) -> list[RunAgentSnapshot]:
        """Build snapshots by querying the seed-state catalog."""
        selected_handles: list[str] = [agent.handle for agent in agents]

        seed_state = hydrate_seed_state(
            agent_repo=self.agent_repo,
            agent_bio_repo=self.agent_bio_repo,
            user_agent_profile_metadata_repo=self.user_agent_profile_metadata_repo,
            handles=selected_handles,
        )
        seed_agent_by_handle = seed_state.agent_by_handle
        latest_bios = seed_state.latest_bios
        metadata_by_agent_id = seed_state.metadata_by_agent_id

        snapshot_rows: list[RunAgentSnapshot] = []
        for selection_order, handle in enumerate(selected_handles):
            seed_agent = seed_agent_by_handle[handle]
            latest_bio = latest_bios.get(seed_agent.agent_id)
            if latest_bio is None:
                raise ValueError(
                    f"Missing latest agent bio for selected agent {seed_agent.agent_id}"
                )

            metadata = metadata_by_agent_id.get(seed_agent.agent_id)
            if metadata is None:
                raise ValueError(
                    "Missing user agent profile metadata for selected agent "
                    f"{seed_agent.agent_id}"
                )

            snapshot_rows.append(
                RunAgentSnapshot(
                    run_id=run.run_id,
                    agent_id=seed_agent.agent_id,
                    selection_order=selection_order,
                    handle_at_start=seed_agent.handle,
                    display_name_at_start=seed_agent.display_name,
                    persona_bio_at_start=latest_bio.persona_bio,
                    followers_count_at_start=metadata.followers_count,
                    follows_count_at_start=metadata.follows_count,
                    posts_count_at_start=metadata.posts_count,
                    created_at=run.created_at,
                )
            )

        return snapshot_rows
