"""Agent action orchestration and LLM-backed proposals for simulation v2."""

from __future__ import annotations

import random
import uuid
from typing import Any

from lib.timestamp_utils import get_current_timestamp
from simulation_v2.agents.constants import (
    MAX_POSTS_TO_LIKE_PER_TURN,
    MAX_POSTS_TO_WRITE_PER_TURN,
    MAX_USERS_TO_FOLLOW_PER_TURN,
    PROB_FOLLOW_USER,
    PROB_LIKE_POST,
    PROB_WRITE_POST,
)
from simulation_v2.agents.llm import invoke_structured
from simulation_v2.agents.prompts import (
    FOLLOW_USERS_PROMPT,
    LIKE_POSTS_PROMPT,
    WRITE_POST_PROMPT,
)
from simulation_v2.agents.validators import (
    validate_follow_user_ids,
    validate_like_post_ids,
)
from simulation_v2.models.actions import (
    AgentTurnActions,
    AllAgentsTurnActions,
    LlmFollowUsersOutput,
    LlmLikePostsOutput,
    LlmWritePostOutput,
)
from simulation_v2.models.feeds import GeneratedFeedsModel
from simulation_v2.models.seed_data import (
    FollowModel,
    LikeModel,
    LoadedUserModel,
    PostModel,
)
from simulation_v2.models.turn import TurnInputsModel


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


def _user_to_dict(user: LoadedUserModel) -> dict[str, Any]:
    return user.model_dump()


def determine_posts_to_like(
    user: dict[str, Any],
    feed: list[dict[str, Any]],
) -> list[LikeModel]:
    """Propose likes via LLM, then stochastically filter each candidate."""
    candidate_likes = propose_like_posts(
        user,
        feed,
        max_likes=MAX_POSTS_TO_LIKE_PER_TURN,
    )
    return [
        like for like in candidate_likes if random.random() < PROB_LIKE_POST
    ]


def determine_posts_to_write(
    user: dict[str, Any],
    feed: list[dict[str, Any]],
) -> list[PostModel]:
    """Optionally propose up to ``MAX_POSTS_TO_WRITE_PER_TURN`` new posts."""
    candidate_posts: list[PostModel] = []
    for _ in range(MAX_POSTS_TO_WRITE_PER_TURN):
        if random.random() < PROB_WRITE_POST:
            candidate_posts.append(propose_write_post(user, feed))
    return candidate_posts


def determine_users_to_follow(
    user: dict[str, Any],
    feed: list[dict[str, Any]],
    all_users: dict[str, LoadedUserModel],
) -> list[FollowModel]:
    """Propose follows for authors seen in the feed, then stochastically filter."""
    author_ids = {
        post["user_id"]
        for post in feed
        if post.get("user_id") and post["user_id"] != user["user_id"]
    }
    candidate_users = [
        _user_to_dict(all_users[author_id])
        for author_id in author_ids
        if author_id in all_users
    ]
    if not candidate_users:
        return []

    candidate_follows = propose_follow_users(
        user,
        candidate_users,
        max_follows=MAX_USERS_TO_FOLLOW_PER_TURN,
    )
    return [
        follow
        for follow in candidate_follows
        if random.random() < PROB_FOLLOW_USER
    ]


def get_agent_actions(
    user: LoadedUserModel,
    feed: list[dict[str, Any]],
    all_users: dict[str, LoadedUserModel],
) -> AgentTurnActions:
    """Run all agent action types for one user."""
    user_dict = _user_to_dict(user)
    return AgentTurnActions(
        likes=determine_posts_to_like(user_dict, feed),
        posts=determine_posts_to_write(user_dict, feed),
        follows=determine_users_to_follow(user_dict, feed, all_users),
    )


def get_agents_actions(
    turn_inputs: TurnInputsModel,
    feeds: GeneratedFeedsModel,
) -> AllAgentsTurnActions:
    """Run agent actions for every user in the simulation."""
    actions_by_user_id: dict[str, AgentTurnActions] = {}
    for user_id, user in turn_inputs.seed_data.users.items():
        feed = feeds.feeds_by_user_id.get(user_id, [])
        actions_by_user_id[user_id] = get_agent_actions(
            user,
            feed,
            turn_inputs.seed_data.users,
        )
    return AllAgentsTurnActions(actions_by_user_id=actions_by_user_id)
