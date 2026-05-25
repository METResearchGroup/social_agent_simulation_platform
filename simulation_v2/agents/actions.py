"""Agent action orchestration and LLM-backed proposals for simulation v2."""

from __future__ import annotations

import logging
import random
import uuid
from typing import Any

import opik
from tqdm import tqdm

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
from simulation_v2.agents.memory.main import fetch_memory
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
from simulation_v2.telemetry.context import SimulationTraceContext
from simulation_v2.telemetry.opik import PROJECT_NAME, is_opik_enabled
from simulation_v2.telemetry.simulation_metrics import record_stochastic_filter

LOGGER = logging.getLogger(__name__)


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


def _update_trace_context(trace_ctx: SimulationTraceContext | None) -> None:
    if trace_ctx is None or not trace_ctx.enabled or not is_opik_enabled():
        return
    opik.update_current_trace(
        thread_id=trace_ctx.run_id,
        metadata={
            "turn_number": trace_ctx.turn_number,
            "run_id": trace_ctx.run_id,
        },
    )


@opik.track(name="propose_like_posts", project_name=PROJECT_NAME)
def propose_like_posts(
    user: dict[str, Any],
    feed: list[dict[str, Any]],
    *,
    max_likes: int,
    trace_ctx: SimulationTraceContext | None = None,
) -> list[LikeModel]:
    """Ask the LLM which feed posts to like and return like records."""
    _update_trace_context(trace_ctx)
    llm_output = invoke_structured(
        LIKE_POSTS_PROMPT,
        LlmLikePostsOutput,
        trace_ctx=trace_ctx,
        action_type="like_posts",
        user_id=user["user_id"],
        name=user["name"],
        username=user["username"],
        num_followers=user.get("num_followers", 0),
        num_follows=user.get("num_follows", 0),
        memory=fetch_memory(user),
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


@opik.track(name="propose_write_post", project_name=PROJECT_NAME)
def propose_write_post(
    user: dict[str, Any],
    feed: list[dict[str, Any]],
    *,
    trace_ctx: SimulationTraceContext | None = None,
    write_attempt_index: int | None = None,
) -> PostModel:
    """Ask the LLM to write a new post and return a post record."""
    _update_trace_context(trace_ctx)
    llm_output = invoke_structured(
        WRITE_POST_PROMPT,
        LlmWritePostOutput,
        trace_ctx=trace_ctx,
        action_type="write_post",
        user_id=user["user_id"],
        write_attempt_index=write_attempt_index,
        name=user["name"],
        username=user["username"],
        memory=fetch_memory(user),
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


@opik.track(name="propose_follow_users", project_name=PROJECT_NAME)
def propose_follow_users(
    user: dict[str, Any],
    candidate_users: list[dict[str, Any]],
    *,
    max_follows: int,
    trace_ctx: SimulationTraceContext | None = None,
) -> list[FollowModel]:
    """Ask the LLM which users to follow and return follow records."""
    _update_trace_context(trace_ctx)
    llm_output = invoke_structured(
        FOLLOW_USERS_PROMPT,
        LlmFollowUsersOutput,
        trace_ctx=trace_ctx,
        action_type="follow_users",
        user_id=user["user_id"],
        name=user["name"],
        username=user["username"],
        num_followers=user.get("num_followers", 0),
        num_follows=user.get("num_follows", 0),
        memory=fetch_memory(user),
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
    *,
    trace_ctx: SimulationTraceContext | None = None,
) -> list[LikeModel]:
    """Propose likes via LLM, then stochastically filter each candidate."""
    candidate_likes = propose_like_posts(
        user,
        feed,
        max_likes=MAX_POSTS_TO_LIKE_PER_TURN,
        trace_ctx=trace_ctx,
    )
    kept_likes = [like for like in candidate_likes if random.random() < PROB_LIKE_POST]
    if trace_ctx is not None:
        record_stochastic_filter(
            action_type="like_posts",
            user_id=user["user_id"],
            proposed=len(candidate_likes),
            kept=len(kept_likes),
            trace_ctx=trace_ctx,
        )
    return kept_likes


def determine_posts_to_write(
    user: dict[str, Any],
    feed: list[dict[str, Any]],
    *,
    trace_ctx: SimulationTraceContext | None = None,
) -> list[PostModel]:
    """Optionally propose up to ``MAX_POSTS_TO_WRITE_PER_TURN`` new posts."""
    candidate_posts: list[PostModel] = []
    llm_attempts = 0
    for attempt_index in range(MAX_POSTS_TO_WRITE_PER_TURN):
        if random.random() < PROB_WRITE_POST:
            llm_attempts += 1
            try:
                candidate_posts.append(
                    propose_write_post(
                        user,
                        feed,
                        trace_ctx=trace_ctx,
                        write_attempt_index=attempt_index,
                    )
                )
            except ValueError:
                continue
    if trace_ctx is not None:
        record_stochastic_filter(
            action_type="write_post",
            user_id=user["user_id"],
            proposed=llm_attempts,
            kept=len(candidate_posts),
            trace_ctx=trace_ctx,
        )
    return candidate_posts


def determine_users_to_follow(
    user: dict[str, Any],
    feed: list[dict[str, Any]],
    all_users: dict[str, LoadedUserModel],
    *,
    trace_ctx: SimulationTraceContext | None = None,
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
        if trace_ctx is not None:
            record_stochastic_filter(
                action_type="follow_users",
                user_id=user["user_id"],
                proposed=0,
                kept=0,
                trace_ctx=trace_ctx,
            )
        return []

    candidate_follows = propose_follow_users(
        user,
        candidate_users,
        max_follows=MAX_USERS_TO_FOLLOW_PER_TURN,
        trace_ctx=trace_ctx,
    )
    kept_follows = [
        follow for follow in candidate_follows if random.random() < PROB_FOLLOW_USER
    ]
    if trace_ctx is not None:
        record_stochastic_filter(
            action_type="follow_users",
            user_id=user["user_id"],
            proposed=len(candidate_follows),
            kept=len(kept_follows),
            trace_ctx=trace_ctx,
        )
    return kept_follows


@opik.track(name="agent_turn", project_name=PROJECT_NAME)
def get_agent_actions(
    user: LoadedUserModel,
    feed: list[dict[str, Any]],
    all_users: dict[str, LoadedUserModel],
    *,
    trace_ctx: SimulationTraceContext | None = None,
) -> AgentTurnActions:
    """Run all agent action types for one user."""
    _update_trace_context(trace_ctx)
    user_dict = _user_to_dict(user)
    return AgentTurnActions(
        likes=determine_posts_to_like(user_dict, feed, trace_ctx=trace_ctx),
        posts=determine_posts_to_write(user_dict, feed, trace_ctx=trace_ctx),
        follows=determine_users_to_follow(
            user_dict,
            feed,
            all_users,
            trace_ctx=trace_ctx,
        ),
    )


def get_agents_actions(
    turn_inputs: TurnInputsModel,
    feeds: GeneratedFeedsModel,
    *,
    trace_ctx: SimulationTraceContext | None = None,
    turn_number: int | None = None,
    show_progress: bool = True,
) -> AllAgentsTurnActions:
    """Run agent actions for every user in the simulation."""
    actions_by_user_id: dict[str, AgentTurnActions] = {}
    users = list(turn_inputs.seed_data.users.items())
    resolved_turn = (
        turn_number
        if turn_number is not None
        else (trace_ctx.turn_number if trace_ctx is not None else None)
    )
    turn_label = resolved_turn if resolved_turn is not None else "?"

    user_iter: Any = users
    if show_progress and users:
        user_iter = tqdm(
            users,
            desc=f"Turn {turn_label} (agents)",
            unit="agent",
            total=len(users),
            leave=False,
        )

    for user_id, user in user_iter:
        feed = feeds.feeds_by_user_id.get(user_id, [])
        LOGGER.info(
            "Running agent actions for user_id=%s turn=%s",
            user_id,
            turn_label,
        )
        actions_by_user_id[user_id] = get_agent_actions(
            user,
            feed,
            turn_inputs.seed_data.users,
            trace_ctx=trace_ctx,
        )
        LOGGER.info(
            "Completed agent actions for user_id=%s turn=%s",
            user_id,
            turn_label,
        )
    return AllAgentsTurnActions(actions_by_user_id=actions_by_user_id)
