from __future__ import annotations

from collections import defaultdict

from db.repositories.interfaces import (
    CommentRepository,
    FollowRepository,
    GeneratedFeedRepository,
    LikeRepository,
    MetricsRepository,
    RunAgentRepository,
    RunFollowEdgeRepository,
    RunPostCommentRepository,
    RunPostLikeRepository,
    RunPostRepository,
    RunRepository,
)
from lib.validation_decorators import validate_inputs
from simulation.core.models.generated.comment import GeneratedComment
from simulation.core.models.generated.follow import GeneratedFollow
from simulation.core.models.generated.like import GeneratedLike
from simulation.core.models.metrics import RunMetrics, TurnMetrics
from simulation.core.models.posts import Post, run_post_snapshot_to_post
from simulation.core.models.run_follow_edges import RunFollowEdgeSnapshot
from simulation.core.models.runs import Run
from simulation.core.models.turns import TurnData, TurnMetadata
from simulation.core.utils.exceptions import RunNotFoundError
from simulation.core.utils.turn_data_hydration import (
    persisted_comment_to_generated,
    persisted_follow_to_generated,
    persisted_like_to_generated,
)
from simulation.core.utils.validators import validate_run_id, validate_turn_number


class SimulationQueryService:
    """Query service for retrieving simulation run and turn data."""

    def __init__(
        self,
        run_repo: RunRepository,
        metrics_repo: MetricsRepository,
        run_post_repo: RunPostRepository,
        run_post_like_repo: RunPostLikeRepository,
        run_post_comment_repo: RunPostCommentRepository,
        generated_feed_repo: GeneratedFeedRepository,
        like_repo: LikeRepository,
        comment_repo: CommentRepository,
        follow_repo: FollowRepository,
        run_follow_edge_repo: RunFollowEdgeRepository,
        run_agent_repo: RunAgentRepository,
    ):
        self.run_repo = run_repo
        self.metrics_repo = metrics_repo
        self.run_post_repo = run_post_repo
        self.run_post_like_repo = run_post_like_repo
        self.run_post_comment_repo = run_post_comment_repo
        self.generated_feed_repo = generated_feed_repo
        self.like_repo = like_repo
        self.comment_repo = comment_repo
        self.follow_repo = follow_repo
        self.run_follow_edge_repo = run_follow_edge_repo
        self.run_agent_repo = run_agent_repo

    @validate_inputs((validate_run_id, "run_id"))
    def get_run(self, run_id: str) -> Run | None:
        """Get a run by its ID."""
        return self.run_repo.get_run(run_id)

    def list_runs(self) -> list[Run]:
        """List all runs."""
        return self.run_repo.list_runs()

    @validate_inputs((validate_run_id, "run_id"), (validate_turn_number, "turn_number"))
    def get_turn_metadata(self, run_id: str, turn_number: int) -> TurnMetadata | None:
        """Get turn metadata for a specific run and turn number."""
        return self.run_repo.get_turn_metadata(run_id, turn_number)

    @validate_inputs((validate_run_id, "run_id"))
    def list_turn_metadata(self, run_id: str) -> list[TurnMetadata]:
        """List all turn metadata for a run in turn order."""
        metadata_list: list[TurnMetadata] = self.run_repo.list_turn_metadata(
            run_id=run_id
        )
        return sorted(metadata_list, key=lambda metadata: metadata.turn_number)

    @validate_inputs((validate_run_id, "run_id"), (validate_turn_number, "turn_number"))
    def get_turn_metrics(self, run_id: str, turn_number: int) -> TurnMetrics | None:
        return self.metrics_repo.get_turn_metrics(run_id, turn_number)

    @validate_inputs((validate_run_id, "run_id"))
    def list_turn_metrics(self, run_id: str) -> list[TurnMetrics]:
        turn_metrics_list: list[TurnMetrics] = self.metrics_repo.list_turn_metrics(
            run_id
        )
        return sorted(turn_metrics_list, key=lambda item: item.turn_number)

    @validate_inputs((validate_run_id, "run_id"))
    def get_run_metrics(self, run_id: str) -> RunMetrics | None:
        return self.metrics_repo.get_run_metrics(run_id)

    @validate_inputs((validate_run_id, "run_id"))
    def list_run_follow_edges(self, run_id: str) -> list[RunFollowEdgeSnapshot]:
        """List frozen run-start follow edges for a run."""
        return self.run_follow_edge_repo.list_run_follow_edges(run_id)

    @validate_inputs((validate_run_id, "run_id"), (validate_turn_number, "turn_number"))
    def get_turn_data(self, run_id: str, turn_number: int) -> TurnData | None:
        """Returns full turn data with feeds and posts."""
        run = self.run_repo.get_run(run_id)
        if run is None:
            raise RunNotFoundError(run_id)

        feeds = self.generated_feed_repo.read_feeds_for_turn(run_id, turn_number)
        if not feeds:
            return None

        run_agents = self.run_agent_repo.list_run_agents(run_id)
        agent_id_to_handle = {ra.agent_id: ra.handle_at_start for ra in run_agents}

        def _handle_for_agent_id(agent_id: str) -> str:
            if agent_id in agent_id_to_handle:
                return agent_id_to_handle[agent_id]
            raise ValueError(
                f"agent_id {agent_id!r} not found in run agents; "
                "unresolved canonical ID in run-agent snapshot"
            )

        post_ids_set: set[str] = set()
        for feed in feeds:
            post_ids_set.update(feed.post_ids)

        post_ids_list = list(post_ids_set)
        run_post_snapshots = self.run_post_repo.read_run_posts_by_ids(
            run_id, post_ids_list
        )
        like_counts = self.run_post_like_repo.count_likes_by_run_post_ids(
            run_id, post_ids_list
        )
        reply_counts = self.run_post_comment_repo.count_comments_by_run_post_ids(
            run_id, post_ids_list
        )
        post_id_to_post = {
            snap.run_post_id: run_post_snapshot_to_post(
                snap,
                like_count=like_counts.get(snap.run_post_id, 0),
                reply_count=reply_counts.get(snap.run_post_id, 0),
            )
            for snap in run_post_snapshots
        }

        feeds_dict: dict[str, list[Post]] = {}
        for feed in feeds:
            hydrated_posts = []
            for post_id in feed.post_ids:
                if post_id in post_id_to_post:
                    hydrated_posts.append(post_id_to_post[post_id])
            feed_key = _handle_for_agent_id(feed.agent_id)
            feeds_dict[feed_key] = hydrated_posts

        actions_by_agent: dict[
            str, list[GeneratedLike | GeneratedComment | GeneratedFollow]
        ] = defaultdict(list)
        for row in self.like_repo.read_likes_by_run_turn(run_id, turn_number):
            actions_by_agent[_handle_for_agent_id(row.agent_id)].append(
                persisted_like_to_generated(row)
            )
        for row in self.comment_repo.read_comments_by_run_turn(run_id, turn_number):
            actions_by_agent[_handle_for_agent_id(row.agent_id)].append(
                persisted_comment_to_generated(row)
            )
        for row in self.follow_repo.read_follows_by_run_turn(run_id, turn_number):
            actions_by_agent[_handle_for_agent_id(row.agent_id)].append(
                persisted_follow_to_generated(row)
            )

        def _action_sort_key(
            a: GeneratedLike | GeneratedComment | GeneratedFollow,
        ) -> tuple[str, str]:
            if isinstance(a, GeneratedLike):
                return (a.like.post_id, a.like.like_id)
            if isinstance(a, GeneratedComment):
                return (a.comment.post_id, a.comment.comment_id)
            if isinstance(a, GeneratedFollow):
                return (a.follow.target_agent_id, a.follow.follow_id)
            raise TypeError(
                f"_action_sort_key only supports GeneratedLike, GeneratedComment, "
                f"GeneratedFollow; got unsupported action type {type(a)!r}"
            )

        actions_dict: dict[str, list] = {
            agent_handle: sorted(agent_actions, key=_action_sort_key)
            for agent_handle, agent_actions in actions_by_agent.items()
        }

        return TurnData(
            turn_number=turn_number,
            agents=[],
            feeds=feeds_dict,
            actions=actions_dict,
        )
