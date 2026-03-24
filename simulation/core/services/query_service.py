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
    TurnPostRepository,
)
from lib.validation_decorators import validate_inputs
from simulation.core.models.feeds import GeneratedFeed
from simulation.core.models.generated.comment import GeneratedComment
from simulation.core.models.generated.follow import GeneratedFollow
from simulation.core.models.generated.like import GeneratedLike
from simulation.core.models.metrics import RunMetrics, TurnMetrics
from simulation.core.models.posts import Post
from simulation.core.models.run_agents import RunAgentSnapshot
from simulation.core.models.run_follow_edges import RunFollowEdgeSnapshot
from simulation.core.models.runs import Run
from simulation.core.models.turns import TurnData, TurnMetadata
from simulation.core.utils.exceptions import RunNotFoundError
from simulation.core.utils.feed_visible_post_hydration import (
    hydrate_feed_visible_posts_for_run,
)
from simulation.core.utils.turn_data_hydration import (
    persisted_comment_to_generated,
    persisted_follow_to_generated,
    persisted_like_to_generated,
)
from simulation.core.utils.validators import validate_run_id, validate_turn_number


class SimulationQueryService:
    """Query service for retrieving simulation run and turn data.

    Turn-scoped feeds and actions are loaded via repositories backed by
    ``turn_generated_feeds`` and ``turn_likes`` / ``turn_comments`` /
    ``turn_follows``. Post bodies for feed cards are resolved from ``run_posts``
    snapshots; ``turn_posts`` is not used on this read path yet.
    """

    def __init__(
        self,
        run_repo: RunRepository,
        metrics_repo: MetricsRepository,
        run_post_repo: RunPostRepository,
        turn_post_repo: TurnPostRepository,
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
        self.turn_post_repo = turn_post_repo
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
    def list_run_agents(self, run_id: str) -> list[RunAgentSnapshot]:
        """List run-start agent snapshots for a run."""
        return self.run_agent_repo.list_run_agents(run_id)

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
        """Return full turn data: feeds, hydrated posts, and actions.

        ``feeds``, ``feed_records``, and ``actions`` are keyed by canonical
        ``agent_id`` only. Feeds and actions are read from the generated-feed
        and action repositories (turn-scoped tables). Post text and metadata
        hydrate from ``run_posts`` first, then ``turn_posts``, for the union of
        feed ``post_ids`` and like/comment ``post_id`` values.
        """
        run = self.run_repo.get_run(run_id)
        if run is None:
            raise RunNotFoundError(run_id)

        feeds: list[GeneratedFeed] = self.generated_feed_repo.read_feeds_for_turn(
            run_id, turn_number
        )
        like_rows = self.like_repo.read_likes_by_run_turn(run_id, turn_number)
        comment_rows = self.comment_repo.read_comments_by_run_turn(run_id, turn_number)
        follow_rows = self.follow_repo.read_follows_by_run_turn(run_id, turn_number)

        if not feeds and not like_rows and not comment_rows and not follow_rows:
            return None

        post_ids_set: set[str] = set()
        for feed in feeds:
            post_ids_set.update(feed.post_ids)
        for row in like_rows:
            post_ids_set.add(row.post_id)
        for row in comment_rows:
            post_ids_set.add(row.post_id)

        post_ids_list = list(post_ids_set)
        post_id_to_post = hydrate_feed_visible_posts_for_run(
            run_id,
            post_ids_list,
            run_post_repo=self.run_post_repo,
            turn_post_repo=self.turn_post_repo,
            run_post_like_repo=self.run_post_like_repo,
            run_post_comment_repo=self.run_post_comment_repo,
        )

        feeds_dict: dict[str, list[Post]] = {}
        feed_records: dict[str, GeneratedFeed] = {}
        for feed in feeds:
            hydrated_posts: list[Post] = []
            for post_id in feed.post_ids:
                if post_id in post_id_to_post:
                    hydrated_posts.append(post_id_to_post[post_id])
            agent_key = feed.agent_id
            feeds_dict[agent_key] = hydrated_posts
            feed_records[agent_key] = feed

        actions_by_agent: dict[
            str, list[GeneratedLike | GeneratedComment | GeneratedFollow]
        ] = defaultdict(list)
        for row in like_rows:
            actions_by_agent[row.agent_id].append(persisted_like_to_generated(row))
        for row in comment_rows:
            actions_by_agent[row.agent_id].append(persisted_comment_to_generated(row))
        for row in follow_rows:
            actions_by_agent[row.agent_id].append(persisted_follow_to_generated(row))

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
            agent_id: sorted(agent_actions, key=_action_sort_key)
            for agent_id, agent_actions in actions_by_agent.items()
        }

        return TurnData(
            turn_number=turn_number,
            agents=[],
            feeds=feeds_dict,
            feed_records=feed_records,
            actions=actions_dict,
        )
