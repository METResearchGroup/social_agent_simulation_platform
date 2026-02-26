from __future__ import annotations

from collections.abc import Callable
from typing import Final, TypeVar, cast

from simulation.core.models.actions import Comment, Follow, Like
from simulation.core.models.generated.base import GenerationMetadata
from simulation.core.models.generated.comment import GeneratedComment
from simulation.core.models.generated.follow import GeneratedFollow
from simulation.core.models.generated.like import GeneratedLike
from simulation.core.models.persisted_actions import (
    PersistedComment,
    PersistedFollow,
    PersistedLike,
)
from tests.factories._helpers import _timestamp_utc_compact
from tests.factories.base import BaseFactory
from tests.factories.context import get_faker
from tests.factories.generated import GenerationMetadataFactory


class _UnsetType:
    pass


UNSET: Final[_UnsetType] = _UnsetType()

_T = TypeVar("_T")


def _resolve_unset(value: _T | _UnsetType, default: Callable[[], _T]) -> _T:
    if isinstance(value, _UnsetType):
        return default()
    return cast(_T, value)


class LikeFactory(BaseFactory[Like]):
    @classmethod
    def create(
        cls,
        *,
        like_id: str | None = None,
        agent_id: str | None = None,
        post_id: str | None = None,
        created_at: str | None = None,
    ) -> Like:
        fake = get_faker()
        agent_value = (
            agent_id if agent_id is not None else f"{fake.user_name()}.bsky.social"
        )
        post_value = post_id if post_id is not None else f"post_{fake.uuid4()}"
        like_id_value = (
            like_id if like_id is not None else f"like_{agent_value}_{post_value}"
        )
        return Like(
            like_id=like_id_value,
            agent_id=agent_value,
            post_id=post_value,
            created_at=created_at
            if created_at is not None
            else _timestamp_utc_compact(),
        )


class CommentFactory(BaseFactory[Comment]):
    @classmethod
    def create(
        cls,
        *,
        comment_id: str | None = None,
        agent_id: str | None = None,
        post_id: str | None = None,
        text: str | None = None,
        created_at: str | None = None,
    ) -> Comment:
        fake = get_faker()
        agent_value = (
            agent_id if agent_id is not None else f"{fake.user_name()}.bsky.social"
        )
        post_value = post_id if post_id is not None else f"post_{fake.uuid4()}"
        comment_id_value = (
            comment_id
            if comment_id is not None
            else f"comment_{agent_value}_{post_value}"
        )
        return Comment(
            comment_id=comment_id_value,
            agent_id=agent_value,
            post_id=post_value,
            text=text if text is not None else fake.sentence(nb_words=6),
            created_at=created_at
            if created_at is not None
            else _timestamp_utc_compact(),
        )


class FollowFactory(BaseFactory[Follow]):
    @classmethod
    def create(
        cls,
        *,
        follow_id: str | None = None,
        agent_id: str | None = None,
        user_id: str | None = None,
        created_at: str | None = None,
    ) -> Follow:
        fake = get_faker()
        agent_value = (
            agent_id if agent_id is not None else f"{fake.user_name()}.bsky.social"
        )
        user_value = (
            user_id if user_id is not None else f"{fake.user_name()}.bsky.social"
        )
        follow_id_value = (
            follow_id if follow_id is not None else f"follow_{agent_value}_{user_value}"
        )
        return Follow(
            follow_id=follow_id_value,
            agent_id=agent_value,
            user_id=user_value,
            created_at=created_at
            if created_at is not None
            else _timestamp_utc_compact(),
        )


class GeneratedLikeFactory(BaseFactory[GeneratedLike]):
    @classmethod
    def create(
        cls,
        *,
        like: Like | None = None,
        explanation: str | None = None,
        metadata: GenerationMetadata | None = None,
        agent_id: str | None = None,
        post_id: str | None = None,
    ) -> GeneratedLike:
        fake = get_faker()
        like_value = (
            like
            if like is not None
            else LikeFactory.create(agent_id=agent_id, post_id=post_id)
        )
        return GeneratedLike(
            like=like_value,
            explanation=explanation
            if explanation is not None
            else fake.sentence(nb_words=8),
            metadata=metadata
            if metadata is not None
            else GenerationMetadataFactory.create(),
        )


class GeneratedCommentFactory(BaseFactory[GeneratedComment]):
    @classmethod
    def create(
        cls,
        *,
        comment: Comment | None = None,
        explanation: str | None = None,
        metadata: GenerationMetadata | None = None,
        agent_id: str | None = None,
        post_id: str | None = None,
        text: str | None = None,
    ) -> GeneratedComment:
        fake = get_faker()
        comment_value = (
            comment
            if comment is not None
            else CommentFactory.create(agent_id=agent_id, post_id=post_id, text=text)
        )
        return GeneratedComment(
            comment=comment_value,
            explanation=explanation
            if explanation is not None
            else fake.sentence(nb_words=8),
            metadata=metadata
            if metadata is not None
            else GenerationMetadataFactory.create(),
        )


class GeneratedFollowFactory(BaseFactory[GeneratedFollow]):
    @classmethod
    def create(
        cls,
        *,
        follow: Follow | None = None,
        explanation: str | None = None,
        metadata: GenerationMetadata | None = None,
        agent_id: str | None = None,
        user_id: str | None = None,
    ) -> GeneratedFollow:
        fake = get_faker()
        follow_value = (
            follow
            if follow is not None
            else FollowFactory.create(agent_id=agent_id, user_id=user_id)
        )
        return GeneratedFollow(
            follow=follow_value,
            explanation=explanation
            if explanation is not None
            else fake.sentence(nb_words=8),
            metadata=metadata
            if metadata is not None
            else GenerationMetadataFactory.create(),
        )


class PersistedLikeFactory(BaseFactory[PersistedLike]):
    @classmethod
    def create(
        cls,
        *,
        like_id: str | None = None,
        run_id: str | None = None,
        turn_number: int = 0,
        agent_handle: str | None = None,
        post_id: str | None = None,
        created_at: str | None = None,
        explanation: str | None | _UnsetType = UNSET,
        model_used: str | None | _UnsetType = UNSET,
        generation_metadata_json: str | None | _UnsetType = UNSET,
        generation_created_at: str | None | _UnsetType = UNSET,
    ) -> PersistedLike:
        fake = get_faker()
        run_value = run_id if run_id is not None else f"run_{fake.uuid4()}"
        agent_value = (
            agent_handle
            if agent_handle is not None
            else f"{fake.user_name()}.bsky.social"
        )
        post_value = post_id if post_id is not None else f"post_{fake.uuid4()}"
        like_id_value = (
            like_id if like_id is not None else f"like_{agent_value}_{post_value}"
        )
        explanation_value = _resolve_unset(
            explanation,
            lambda: fake.sentence(nb_words=8),
        )
        model_used_value = _resolve_unset(model_used, lambda: "test-model")
        generation_metadata_json_value = _resolve_unset(
            generation_metadata_json,
            lambda: '{"seed": 1}',
        )
        generation_created_at_value = _resolve_unset(
            generation_created_at,
            lambda: _timestamp_utc_compact(),
        )
        return PersistedLike(
            like_id=like_id_value,
            run_id=run_value,
            turn_number=turn_number,
            agent_handle=agent_value,
            post_id=post_value,
            created_at=created_at
            if created_at is not None
            else _timestamp_utc_compact(),
            explanation=explanation_value,
            model_used=model_used_value,
            generation_metadata_json=generation_metadata_json_value,
            generation_created_at=generation_created_at_value,
        )


class PersistedCommentFactory(BaseFactory[PersistedComment]):
    @classmethod
    def create(
        cls,
        *,
        comment_id: str | None = None,
        run_id: str | None = None,
        turn_number: int = 0,
        agent_handle: str | None = None,
        post_id: str | None = None,
        text: str | None = None,
        created_at: str | None = None,
        explanation: str | None | _UnsetType = UNSET,
        model_used: str | None | _UnsetType = UNSET,
        generation_metadata_json: str | None | _UnsetType = UNSET,
        generation_created_at: str | None | _UnsetType = UNSET,
    ) -> PersistedComment:
        fake = get_faker()
        run_value = run_id if run_id is not None else f"run_{fake.uuid4()}"
        agent_value = (
            agent_handle
            if agent_handle is not None
            else f"{fake.user_name()}.bsky.social"
        )
        post_value = post_id if post_id is not None else f"post_{fake.uuid4()}"
        comment_id_value = (
            comment_id
            if comment_id is not None
            else f"comment_{agent_value}_{post_value}"
        )
        explanation_value = _resolve_unset(
            explanation,
            lambda: fake.sentence(nb_words=8),
        )
        model_used_value = _resolve_unset(model_used, lambda: "test-model")
        generation_metadata_json_value = _resolve_unset(
            generation_metadata_json,
            lambda: '{"seed": 1}',
        )
        generation_created_at_value = _resolve_unset(
            generation_created_at,
            lambda: _timestamp_utc_compact(),
        )
        return PersistedComment(
            comment_id=comment_id_value,
            run_id=run_value,
            turn_number=turn_number,
            agent_handle=agent_value,
            post_id=post_value,
            text=text if text is not None else fake.sentence(nb_words=6),
            created_at=created_at
            if created_at is not None
            else _timestamp_utc_compact(),
            explanation=explanation_value,
            model_used=model_used_value,
            generation_metadata_json=generation_metadata_json_value,
            generation_created_at=generation_created_at_value,
        )


class PersistedFollowFactory(BaseFactory[PersistedFollow]):
    @classmethod
    def create(
        cls,
        *,
        follow_id: str | None = None,
        run_id: str | None = None,
        turn_number: int = 0,
        agent_handle: str | None = None,
        user_id: str | None = None,
        created_at: str | None = None,
        explanation: str | None | _UnsetType = UNSET,
        model_used: str | None | _UnsetType = UNSET,
        generation_metadata_json: str | None | _UnsetType = UNSET,
        generation_created_at: str | None | _UnsetType = UNSET,
    ) -> PersistedFollow:
        fake = get_faker()
        run_value = run_id if run_id is not None else f"run_{fake.uuid4()}"
        agent_value = (
            agent_handle
            if agent_handle is not None
            else f"{fake.user_name()}.bsky.social"
        )
        user_value = (
            user_id if user_id is not None else f"{fake.user_name()}.bsky.social"
        )
        follow_id_value = (
            follow_id if follow_id is not None else f"follow_{agent_value}_{user_value}"
        )
        explanation_value = _resolve_unset(
            explanation,
            lambda: fake.sentence(nb_words=8),
        )
        model_used_value = _resolve_unset(model_used, lambda: "test-model")
        generation_metadata_json_value = _resolve_unset(
            generation_metadata_json,
            lambda: '{"seed": 1}',
        )
        generation_created_at_value = _resolve_unset(
            generation_created_at,
            lambda: _timestamp_utc_compact(),
        )
        return PersistedFollow(
            follow_id=follow_id_value,
            run_id=run_value,
            turn_number=turn_number,
            agent_handle=agent_value,
            user_id=user_value,
            created_at=created_at
            if created_at is not None
            else _timestamp_utc_compact(),
            explanation=explanation_value,
            model_used=model_used_value,
            generation_metadata_json=generation_metadata_json_value,
            generation_created_at=generation_created_at_value,
        )
