"""Pure business-rule validators for LLM-proposed actions."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

FilterId = Literal[
    "no_self_like",
    "duplicate_like",
    "missing_target_post",
    "no_self_follow",
    "duplicate_follow",
    "missing_target_user",
    "empty_content",
    "missing_parent_post",
    "max_actions_per_turn",
    "unsupported_action_type",
]


class ActionValidationOutcome(BaseModel):
    accepted: bool
    filter_id: FilterId | None = None
    filter_reason: str | None = None


def validate_like_post_action(
    *,
    user_id: str,
    post_id: str,
    feed_post_ids: set[str],
    feed_author_by_post_id: dict[str, str],
    snapshot_liked_post_ids: set[str],
    accepted_likes_this_turn: set[str],
    accepted_like_count: int,
    max_likes: int,
) -> ActionValidationOutcome:
    if accepted_like_count >= max_likes:
        return ActionValidationOutcome(
            accepted=False,
            filter_id="max_actions_per_turn",
            filter_reason=f"Exceeded max like_post per turn ({max_likes})",
        )
    if post_id in accepted_likes_this_turn:
        return ActionValidationOutcome(
            accepted=False,
            filter_id="duplicate_like",
            filter_reason=f"Duplicate like for post {post_id}",
        )
    if post_id not in feed_post_ids:
        return ActionValidationOutcome(
            accepted=False,
            filter_id="missing_target_post",
            filter_reason=f"Post {post_id} not in feed",
        )
    author_id = feed_author_by_post_id.get(post_id)
    if author_id == user_id:
        return ActionValidationOutcome(
            accepted=False,
            filter_id="no_self_like",
            filter_reason="Cannot like your own post",
        )
    if post_id in snapshot_liked_post_ids:
        return ActionValidationOutcome(
            accepted=False,
            filter_id="duplicate_like",
            filter_reason=f"Duplicate like for post {post_id}",
        )
    return ActionValidationOutcome(accepted=True)


def validate_follow_user_action(
    *,
    user_id: str,
    followee_id: str,
    follow_candidate_ids: set[str],
    snapshot_followed_user_ids: set[str],
    accepted_follows_this_turn: set[str],
    accepted_follow_count: int,
    max_follows: int,
) -> ActionValidationOutcome:
    if accepted_follow_count >= max_follows:
        return ActionValidationOutcome(
            accepted=False,
            filter_id="max_actions_per_turn",
            filter_reason=f"Exceeded max follow_user per turn ({max_follows})",
        )
    if followee_id in accepted_follows_this_turn:
        return ActionValidationOutcome(
            accepted=False,
            filter_id="duplicate_follow",
            filter_reason=f"Duplicate follow for user {followee_id}",
        )
    if followee_id == user_id:
        return ActionValidationOutcome(
            accepted=False,
            filter_id="no_self_follow",
            filter_reason="Cannot follow yourself",
        )
    if followee_id not in follow_candidate_ids:
        return ActionValidationOutcome(
            accepted=False,
            filter_id="missing_target_user",
            filter_reason=f"User {followee_id} not in follow candidates",
        )
    if followee_id in snapshot_followed_user_ids:
        return ActionValidationOutcome(
            accepted=False,
            filter_id="duplicate_follow",
            filter_reason=f"Duplicate follow for user {followee_id}",
        )
    return ActionValidationOutcome(accepted=True)


def validate_write_post_action(
    *,
    content: str | None,
    accepted_write_count: int,
    max_posts: int,
) -> ActionValidationOutcome:
    if not (content or "").strip():
        return ActionValidationOutcome(
            accepted=False,
            filter_id="empty_content",
            filter_reason="Action content is empty",
        )
    if accepted_write_count >= max_posts:
        return ActionValidationOutcome(
            accepted=False,
            filter_id="max_actions_per_turn",
            filter_reason=f"Exceeded max write_post per turn ({max_posts})",
        )
    return ActionValidationOutcome(accepted=True)


def validate_comment_on_post_action(
    *,
    parent_post_id: str,
    content: str | None,
    feed_post_ids: set[str],
    accepted_comment_count: int,
    max_comments: int,
) -> ActionValidationOutcome:
    if not (content or "").strip():
        return ActionValidationOutcome(
            accepted=False,
            filter_id="empty_content",
            filter_reason="Action content is empty",
        )
    if parent_post_id not in feed_post_ids:
        return ActionValidationOutcome(
            accepted=False,
            filter_id="missing_parent_post",
            filter_reason=f"Parent post {parent_post_id} not in feed",
        )
    if accepted_comment_count >= max_comments:
        return ActionValidationOutcome(
            accepted=False,
            filter_id="max_actions_per_turn",
            filter_reason=f"Exceeded max comment_on_post per turn ({max_comments})",
        )
    return ActionValidationOutcome(accepted=True)
