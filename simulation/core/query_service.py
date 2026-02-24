from __future__ import annotations

import json
from collections import defaultdict

from db.repositories.interfaces import (
    CommentRepository,
    FeedPostRepository,
    FollowRepository,
    GeneratedFeedRepository,
    LikeRepository,
    MetricsRepository,
    RunRepository,
)
from lib.validation_decorators import validate_inputs
from simulation.core.exceptions import RunNotFoundError
from simulation.core.models.actions import Comment, Follow, Like
from simulation.core.models.generated.base import GenerationMetadata
from simulation.core.models.generated.comment import GeneratedComment
from simulation.core.models.generated.follow import GeneratedFollow
from simulation.core.models.generated.like import GeneratedLike
from simulation.core.models.metrics import RunMetrics, TurnMetrics
from simulation.core.models.persisted_actions import (
    PersistedComment,
    PersistedFollow,
    PersistedLike,
)
from simulation.core.models.posts import BlueskyFeedPost
from simulation.core.models.runs import Run
from simulation.core.models.turns import TurnData, TurnMetadata
from simulation.core.validators import validate_run_id, validate_turn_number


def _persisted_like_to_generated(row: PersistedLike) -> GeneratedLike:
    """Build GeneratedLike from a PersistedLike row."""
    meta_dict = (
        json.loads(row.generation_metadata_json)
        if row.generation_metadata_json
        else None
    )
    metadata = GenerationMetadata(
        model_used=row.model_used,
        generation_metadata=meta_dict,
        created_at=row.generation_created_at or row.created_at,
    )
    return GeneratedLike(
        like=Like(
            like_id=row.like_id,
            agent_id=row.agent_handle,
            post_id=row.post_id,
            created_at=row.created_at,
        ),
        explanation=row.explanation or "",
        metadata=metadata,
    )


def _persisted_comment_to_generated(row: PersistedComment) -> GeneratedComment:
    """Build GeneratedComment from a PersistedComment row."""
    meta_dict = (
        json.loads(row.generation_metadata_json)
        if row.generation_metadata_json
        else None
    )
    metadata = GenerationMetadata(
        model_used=row.model_used,
        generation_metadata=meta_dict,
        created_at=row.generation_created_at or row.created_at,
    )
    return GeneratedComment(
        comment=Comment(
            comment_id=row.comment_id,
            agent_id=row.agent_handle,
            post_id=row.post_id,
            text=row.text,
            created_at=row.created_at,
        ),
        explanation=row.explanation or "",
        metadata=metadata,
    )


def _persisted_follow_to_generated(row: PersistedFollow) -> GeneratedFollow:
    """Build GeneratedFollow from a PersistedFollow row."""
    meta_dict = (
        json.loads(row.generation_metadata_json)
        if row.generation_metadata_json
        else None
    )
    metadata = GenerationMetadata(
        model_used=row.model_used,
        generation_metadata=meta_dict,
        created_at=row.generation_created_at or row.created_at,
    )
    return GeneratedFollow(
        follow=Follow(
            follow_id=row.follow_id,
            agent_id=row.agent_handle,
            user_id=row.user_id,
            created_at=row.created_at,
        ),
        explanation=row.explanation or "",
        metadata=metadata,
    )


class SimulationQueryService:
    """Query service for retrieving simulation run and turn data."""

    def __init__(
        self,
        run_repo: RunRepository,
        metrics_repo: MetricsRepository,
        feed_post_repo: FeedPostRepository,
        generated_feed_repo: GeneratedFeedRepository,
        like_repo: LikeRepository | None = None,
        comment_repo: CommentRepository | None = None,
        follow_repo: FollowRepository | None = None,
    ):
        self.run_repo = run_repo
        self.metrics_repo = metrics_repo
        self.feed_post_repo = feed_post_repo
        self.generated_feed_repo = generated_feed_repo
        self._like_repo = like_repo
        self._comment_repo = comment_repo
        self._follow_repo = follow_repo

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

    @validate_inputs((validate_run_id, "run_id"), (validate_turn_number, "turn_number"))
    def get_turn_data(self, run_id: str, turn_number: int) -> TurnData | None:
        """Returns full turn data with feeds and posts."""
        run = self.run_repo.get_run(run_id)
        if run is None:
            raise RunNotFoundError(run_id)

        feeds = self.generated_feed_repo.read_feeds_for_turn(run_id, turn_number)
        if not feeds:
            return None

        post_uris_set: set[str] = set()
        for feed in feeds:
            post_uris_set.update(feed.post_uris)

        post_uris_list = list(post_uris_set)
        posts = self.feed_post_repo.read_feed_posts_by_uris(post_uris_list)

        uri_to_post = {post.uri: post for post in posts}

        feeds_dict: dict[str, list[BlueskyFeedPost]] = {}
        for feed in feeds:
            hydrated_posts = []
            for post_uri in feed.post_uris:
                if post_uri in uri_to_post:
                    hydrated_posts.append(uri_to_post[post_uri])
            feeds_dict[feed.agent_handle] = hydrated_posts

        actions_by_agent: dict[
            str, list[GeneratedLike | GeneratedComment | GeneratedFollow]
        ] = defaultdict(list)
        if self._like_repo is not None:
            for row in self._like_repo.read_likes_by_run_turn(run_id, turn_number):
                actions_by_agent[row.agent_handle].append(
                    _persisted_like_to_generated(row)
                )
        if self._comment_repo is not None:
            for row in self._comment_repo.read_comments_by_run_turn(
                run_id, turn_number
            ):
                actions_by_agent[row.agent_handle].append(
                    _persisted_comment_to_generated(row)
                )
        if self._follow_repo is not None:
            for row in self._follow_repo.read_follows_by_run_turn(run_id, turn_number):
                actions_by_agent[row.agent_handle].append(
                    _persisted_follow_to_generated(row)
                )

        def _action_sort_key(
            a: GeneratedLike | GeneratedComment | GeneratedFollow,
        ) -> tuple[str, str]:
            if isinstance(a, GeneratedLike):
                return (a.like.post_id, a.like.like_id)
            if isinstance(a, GeneratedComment):
                return (a.comment.post_id, a.comment.comment_id)
            return (a.follow.user_id, a.follow.follow_id)

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
