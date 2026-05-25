"""LLM-backed agent action proposals for simulation v2."""

from __future__ import annotations

import uuid
from typing import Any

from lib.timestamp_utils import get_current_timestamp
from simulation_v2.agents.llm import invoke_structured
from simulation_v2.agents.prompts import (
    FOLLOW_USERS_PROMPT,
    LIKE_POSTS_PROMPT,
    WRITE_POST_PROMPT,
)
from simulation_v2.models.actions import (
    LlmFollowUsersOutput,
    LlmLikePostsOutput,
    LlmWritePostOutput,
)
from simulation_v2.models.seed_data import FollowModel, LikeModel, PostModel


def _format_feed_posts(feed: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for post in feed:
        excerpt = str(post.get("content", ""))[:120]
        lines.append(
            f"{post['post_id']} | {post.get('user_id', '')} | "
            f"{post.get('num_likes', 0)} likes | {excerpt}"
        )
    return "\n".join(lines) if lines else "No posts in feed."


def _format_candidate_users(
    users: list[dict[str, Any]],
) -> str:
    lines: list[str] = []
    for user in users:
        lines.append(
            f"{user['user_id']} | @{user.get('username', '')} | {user.get('name', '')}"
        )
    return "\n".join(lines) if lines else "No candidate users."


def validate_like_post_ids(
    post_ids: list[str],
    *,
    user_id: str,
    feed: list[dict[str, Any]],
    max_likes: int,
) -> list[str]:
    """Keep only valid, non-self feed post IDs."""
    feed_by_id = {post["post_id"]: post for post in feed}
    validated: list[str] = []
    seen: set[str] = set()
    for post_id in post_ids:
        if len(validated) >= max_likes:
            break
        if post_id in seen:
            continue
        post = feed_by_id.get(post_id)
        if post is None:
            continue
        if post.get("user_id") == user_id:
            continue
        validated.append(post_id)
        seen.add(post_id)
    return validated


def validate_follow_user_ids(
    user_ids: list[str],
    *,
    user_id: str,
    candidates: list[dict[str, Any]],
    max_follows: int,
) -> list[str]:
    """Keep only valid, non-self candidate user IDs."""
    candidate_ids = {user["user_id"] for user in candidates}
    validated: list[str] = []
    seen: set[str] = set()
    for candidate_id in user_ids:
        if len(validated) >= max_follows:
            break
        if candidate_id in seen:
            continue
        if candidate_id == user_id:
            continue
        if candidate_id not in candidate_ids:
            continue
        validated.append(candidate_id)
        seen.add(candidate_id)
    return validated


def propose_like_posts(
    user: dict[str, Any],
    feed: list[dict[str, Any]],
    *,
    max_likes: int,
) -> list[LikeModel]:
    """Ask the LLM which feed posts to like and return like records."""
    llm_output = invoke_structured(
        LIKE_POSTS_PROMPT,
        LlmLikePostsOutput,
        name=user["name"],
        username=user["username"],
        num_followers=user.get("num_followers", 0),
        num_follows=user.get("num_follows", 0),
        feed_posts=_format_feed_posts(feed),
        max_likes=max_likes,
    )
    validated_post_ids = validate_like_post_ids(
        llm_output.post_ids,
        user_id=user["user_id"],
        feed=feed,
        max_likes=max_likes,
    )
    created_at = get_current_timestamp()
    return [
        LikeModel(
            like_id=str(uuid.uuid4()),
            user_id=user["user_id"],
            post_id=post_id,
            created_at=created_at,
        )
        for post_id in validated_post_ids
    ]


def propose_write_post(
    user: dict[str, Any],
    feed: list[dict[str, Any]],
) -> PostModel:
    """Ask the LLM to write a new post and return a post record."""
    llm_output = invoke_structured(
        WRITE_POST_PROMPT,
        LlmWritePostOutput,
        name=user["name"],
        username=user["username"],
        feed_posts=_format_feed_posts(feed),
    )
    content = llm_output.content.strip()
    if not content:
        raise ValueError("LLM returned empty post content")
    return PostModel(
        post_id=str(uuid.uuid4()),
        user_id=user["user_id"],
        content=content,
        created_at=get_current_timestamp(),
    )


def propose_follow_users(
    user: dict[str, Any],
    candidate_users: list[dict[str, Any]],
    *,
    max_follows: int,
) -> list[FollowModel]:
    """Ask the LLM which users to follow and return follow records."""
    llm_output = invoke_structured(
        FOLLOW_USERS_PROMPT,
        LlmFollowUsersOutput,
        name=user["name"],
        username=user["username"],
        num_followers=user.get("num_followers", 0),
        num_follows=user.get("num_follows", 0),
        candidate_users=_format_candidate_users(candidate_users),
        max_follows=max_follows,
    )
    validated_user_ids = validate_follow_user_ids(
        llm_output.user_ids,
        user_id=user["user_id"],
        candidates=candidate_users,
        max_follows=max_follows,
    )
    return [
        FollowModel(follower_id=user["user_id"], followee_id=followee_id)
        for followee_id in validated_user_ids
    ]
