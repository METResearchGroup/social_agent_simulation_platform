"""Agent action orchestration for simulation v2."""

from __future__ import annotations

import random
from typing import Any

from simulation_v2.agents.actions import (
    propose_follow_users,
    propose_like_posts,
    propose_write_post,
)
from simulation_v2.models.actions import AgentTurnActions, AllAgentsTurnActions
from simulation_v2.models.feeds import GeneratedFeedsModel
from simulation_v2.models.seed_data import (
    FollowModel,
    LikeModel,
    LoadedUserModel,
    PostModel,
)
from simulation_v2.models.turn import TurnInputsModel

PROB_LIKE_POST = 0.25
PROB_WRITE_POST = 0.05
PROB_FOLLOW_USER = 0.02

MAX_POSTS_TO_LIKE_PER_TURN = 10
MAX_POSTS_TO_WRITE_PER_TURN = 5
MAX_USERS_TO_FOLLOW_PER_TURN = 5


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

