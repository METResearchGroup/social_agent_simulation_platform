"""Validation helpers for LLM-proposed agent actions."""

from __future__ import annotations

from typing import Any


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
