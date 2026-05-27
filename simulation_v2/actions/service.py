"""Action LLM generation orchestration and persistence."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Any

from simulation_v2.actions.llm import invoke_structured_generation
from simulation_v2.actions.models import (
    ActionType,
    LlmCommentOnPostOutput,
    LlmFollowUserOutput,
    LlmGenerationResult,
    LlmLikePostOutput,
    LlmWritePostOutput,
)
from simulation_v2.actions.prompts import (
    COMMENT_ON_POST_PROMPT,
    FOLLOW_USERS_PROMPT,
    LIKE_POSTS_PROMPT,
    WRITE_POST_PROMPT,
)
from simulation_v2.actions.validators import (
    ActionValidationOutcome,
    validate_comment_on_post_action,
    validate_follow_user_action,
    validate_like_post_action,
    validate_write_post_action,
)
from simulation_v2.config import ActionConfig, LlmConfig
from simulation_v2.db.models import (
    FeedPostView,
    GeneratedFeedRecord,
    GenerationRecord,
    LlmProposedActionRecord,
    ProposedActionRecord,
    UserRecord,
)
from simulation_v2.db.repositories import SimulationRepositories
from simulation_v2.ids import (
    new_action_id,
    new_generation_id,
    new_llm_proposed_action_id,
)
from simulation_v2.lib.decorators import progress_items
from simulation_v2.memory.service import fetch_memory_for_prompt
from simulation_v2.telemetry.context import SimulationTraceContext
from simulation_v2.time import get_current_timestamp
from simulation_v2.worker.state import TurnStateSnapshot


def generate_and_persist_llm_actions(
    snapshot: TurnStateSnapshot,
    feed_records: list[GeneratedFeedRecord],
    action_config: ActionConfig,
    llm_config: LlmConfig,
    repos: SimulationRepositories,
    conn: sqlite3.Connection,
    *,
    trace_ctx: SimulationTraceContext | None = None,
) -> list[GenerationRecord]:
    feeds_by_user = {record.user_id: record.feed_posts for record in feed_records}
    generation_records: list[GenerationRecord] = []
    user_ids = list(snapshot.users.keys())

    for user_id in progress_items(
        user_ids,
        desc=f"Turn {snapshot.turn_number} (actions)",
        unit="user",
        leave=False,
    ):
        user = snapshot.users[user_id]
        feed_posts = feeds_by_user.get(user_id, [])
        memory = snapshot.agent_memories.get(user_id)
        memory_text = fetch_memory_for_prompt(memory)
        num_followers, num_follows = _follow_counts(user)

        _append_generation(
            generation_records,
            _generate_and_persist_likes(
                snapshot=snapshot,
                user_id=user_id,
                user=user,
                feed_posts=feed_posts,
                memory_text=memory_text,
                num_followers=num_followers,
                num_follows=num_follows,
                action_config=action_config,
                llm_config=llm_config,
                repos=repos,
                conn=conn,
                trace_ctx=trace_ctx,
            ),
        )
        _append_generation(
            generation_records,
            _generate_and_persist_write_post(
                snapshot=snapshot,
                user_id=user_id,
                user=user,
                feed_posts=feed_posts,
                memory_text=memory_text,
                action_config=action_config,
                llm_config=llm_config,
                repos=repos,
                conn=conn,
                trace_ctx=trace_ctx,
            ),
        )
        _append_generation(
            generation_records,
            _generate_and_persist_follows(
                snapshot=snapshot,
                user_id=user_id,
                user=user,
                feed_posts=feed_posts,
                memory_text=memory_text,
                num_followers=num_followers,
                num_follows=num_follows,
                action_config=action_config,
                llm_config=llm_config,
                repos=repos,
                conn=conn,
                trace_ctx=trace_ctx,
            ),
        )
        _append_generation(
            generation_records,
            _generate_and_persist_comments(
                snapshot=snapshot,
                user_id=user_id,
                user=user,
                feed_posts=feed_posts,
                memory_text=memory_text,
                action_config=action_config,
                llm_config=llm_config,
                repos=repos,
                conn=conn,
                trace_ctx=trace_ctx,
            ),
        )

    return generation_records


def validate_and_persist_proposed_actions(
    snapshot: TurnStateSnapshot,
    feed_records: list[GeneratedFeedRecord],
    action_config: ActionConfig,
    repos: SimulationRepositories,
    conn: sqlite3.Connection,
) -> list[ProposedActionRecord]:
    feeds_by_user = {record.user_id: record.feed_posts for record in feed_records}
    llm_rows = repos.list_llm_proposed_actions_for_turn(
        snapshot.run_id, snapshot.turn_id, conn
    )
    llm_rows.sort(key=lambda row: (row.created_at, row.llm_proposed_action_id))

    user_states: dict[str, _UserValidationState] = {}
    proposed_records: list[ProposedActionRecord] = []

    for llm_row in llm_rows:
        state = _get_user_validation_state(
            user_states,
            llm_row.user_id,
            feeds_by_user,
            snapshot,
        )
        outcome = _validate_llm_row(llm_row, state, action_config)
        record = _llm_row_to_proposed_record(outcome, llm_row)
        repos.insert_proposed_action(record, conn)
        proposed_records.append(record)
        if outcome.accepted:
            _record_accepted_action(state, llm_row)

    return proposed_records


@dataclass
class _UserValidationState:
    feed_post_ids: set[str]
    feed_author_by_post_id: dict[str, str]
    follow_candidate_ids: set[str]
    snapshot_liked_post_ids: set[str]
    snapshot_followed_user_ids: set[str]
    accepted_likes: set[str] = field(default_factory=set)
    accepted_follows: set[str] = field(default_factory=set)
    accepted_like_count: int = 0
    accepted_follow_count: int = 0
    accepted_write_count: int = 0
    accepted_comment_count: int = 0


def _get_user_validation_state(
    user_states: dict[str, _UserValidationState],
    user_id: str,
    feeds_by_user: dict[str, list[FeedPostView]],
    snapshot: TurnStateSnapshot,
) -> _UserValidationState:
    if user_id not in user_states:
        feed_posts = feeds_by_user.get(user_id, [])
        candidates = _candidate_users_from_feed(user_id, feed_posts, snapshot.users)
        user_states[user_id] = _UserValidationState(
            feed_post_ids={post.post_id for post in feed_posts},
            feed_author_by_post_id={
                post.post_id: post.author_id for post in feed_posts
            },
            follow_candidate_ids={user.user_id for user in candidates},
            snapshot_liked_post_ids={
                like.post_id for like in snapshot.likes if like.author_id == user_id
            },
            snapshot_followed_user_ids={
                follow.followee_id
                for follow in snapshot.follows
                if follow.follower_id == user_id
            },
        )
    return user_states[user_id]


def _validate_llm_row(
    llm_row: LlmProposedActionRecord,
    state: _UserValidationState,
    action_config: ActionConfig,
) -> ActionValidationOutcome:
    if llm_row.action_type == "like_post":
        return validate_like_post_action(
            user_id=llm_row.user_id,
            post_id=llm_row.target_id or "",
            feed_post_ids=state.feed_post_ids,
            feed_author_by_post_id=state.feed_author_by_post_id,
            snapshot_liked_post_ids=state.snapshot_liked_post_ids,
            accepted_likes_this_turn=state.accepted_likes,
            accepted_like_count=state.accepted_like_count,
            max_likes=action_config.max_likes_per_turn,
        )
    if llm_row.action_type == "follow_user":
        return validate_follow_user_action(
            user_id=llm_row.user_id,
            followee_id=llm_row.target_id or "",
            follow_candidate_ids=state.follow_candidate_ids,
            snapshot_followed_user_ids=state.snapshot_followed_user_ids,
            accepted_follows_this_turn=state.accepted_follows,
            accepted_follow_count=state.accepted_follow_count,
            max_follows=action_config.max_follows_per_turn,
        )
    if llm_row.action_type == "write_post":
        return validate_write_post_action(
            content=llm_row.target_content,
            accepted_write_count=state.accepted_write_count,
            max_posts=action_config.max_posts_per_turn,
        )
    if llm_row.action_type == "comment_on_post":
        return validate_comment_on_post_action(
            parent_post_id=llm_row.target_id or "",
            content=llm_row.target_content,
            feed_post_ids=state.feed_post_ids,
            accepted_comment_count=state.accepted_comment_count,
            max_comments=action_config.max_comments_per_turn,
        )
    return ActionValidationOutcome(
        accepted=False,
        filter_id="unsupported_action_type",
        filter_reason=f"Unsupported action type {llm_row.action_type!r}",
    )


def _record_accepted_action(
    state: _UserValidationState,
    llm_row: LlmProposedActionRecord,
) -> None:
    if llm_row.action_type == "like_post" and llm_row.target_id is not None:
        state.accepted_likes.add(llm_row.target_id)
        state.accepted_like_count += 1
    elif llm_row.action_type == "follow_user" and llm_row.target_id is not None:
        state.accepted_follows.add(llm_row.target_id)
        state.accepted_follow_count += 1
    elif llm_row.action_type == "write_post":
        state.accepted_write_count += 1
    elif llm_row.action_type == "comment_on_post":
        state.accepted_comment_count += 1


def _llm_row_to_proposed_record(
    outcome: ActionValidationOutcome,
    llm_row: LlmProposedActionRecord,
) -> ProposedActionRecord:
    if outcome.accepted:
        return ProposedActionRecord(
            action_id=new_action_id(),
            record_kind="validated",
            generation_id=llm_row.generation_id,
            run_id=llm_row.run_id,
            turn_id=llm_row.turn_id,
            user_id=llm_row.user_id,
            action_type=llm_row.action_type,
            target_type=llm_row.target_type,
            target_id=llm_row.target_id,
            target_content=llm_row.target_content,
            metadata_json=llm_row.metadata_json,
            created_at=get_current_timestamp(),
        )
    return ProposedActionRecord(
        action_id=new_action_id(),
        record_kind="rejected",
        generation_id=llm_row.generation_id,
        run_id=llm_row.run_id,
        turn_id=llm_row.turn_id,
        user_id=llm_row.user_id,
        action_type=llm_row.action_type,
        target_type=llm_row.target_type,
        target_id=llm_row.target_id,
        target_content=llm_row.target_content,
        filter_id=outcome.filter_id,
        filter_reason=outcome.filter_reason,
        rejection_stage="business_rules",
        metadata_json=llm_row.metadata_json,
        created_at=get_current_timestamp(),
    )


def _append_generation(
    records: list[GenerationRecord],
    record: GenerationRecord | None,
) -> None:
    if record is not None:
        records.append(record)


def _generate_and_persist_likes(
    *,
    snapshot: TurnStateSnapshot,
    user_id: str,
    user: UserRecord,
    feed_posts: list[FeedPostView],
    memory_text: str,
    num_followers: int,
    num_follows: int,
    action_config: ActionConfig,
    llm_config: LlmConfig,
    repos: SimulationRepositories,
    conn: sqlite3.Connection,
    trace_ctx: SimulationTraceContext | None = None,
) -> GenerationRecord | None:
    if not action_config.enable_like_post:
        return None

    result = invoke_structured_generation(
        LIKE_POSTS_PROMPT,
        LlmLikePostOutput,
        llm_config=llm_config,
        prompt_variables={
            "name": user.name,
            "username": user.username,
            "num_followers": num_followers,
            "num_follows": num_follows,
            "memory": memory_text,
            "feed_posts": _format_feed_posts(feed_posts),
            "max_likes": action_config.max_likes_per_turn,
        },
        action_type="like_post",
        user_id=user_id,
        trace_ctx=trace_ctx,
    )
    generation = _persist_generation(
        snapshot, user_id, "like_post", result, repos, conn
    )
    if result.status == "completed" and isinstance(result.parsed, LlmLikePostOutput):
        _persist_llm_proposed_actions(
            snapshot,
            user_id,
            "like_post",
            generation.generation_id,
            result.parsed.post_ids,
            repos,
            conn,
        )
    return generation


def _generate_and_persist_write_post(
    *,
    snapshot: TurnStateSnapshot,
    user_id: str,
    user: UserRecord,
    feed_posts: list[FeedPostView],
    memory_text: str,
    action_config: ActionConfig,
    llm_config: LlmConfig,
    repos: SimulationRepositories,
    conn: sqlite3.Connection,
    trace_ctx: SimulationTraceContext | None = None,
) -> GenerationRecord | None:
    if not action_config.enable_write_post:
        return None

    result = invoke_structured_generation(
        WRITE_POST_PROMPT,
        LlmWritePostOutput,
        llm_config=llm_config,
        prompt_variables={
            "name": user.name,
            "username": user.username,
            "memory": memory_text,
            "feed_posts": _format_feed_posts(feed_posts),
        },
        action_type="write_post",
        user_id=user_id,
        trace_ctx=trace_ctx,
    )
    generation = _persist_generation(
        snapshot, user_id, "write_post", result, repos, conn
    )
    if result.status == "completed" and isinstance(result.parsed, LlmWritePostOutput):
        _persist_llm_proposed_actions_write(
            snapshot,
            user_id,
            generation.generation_id,
            result.parsed.content,
            repos,
            conn,
        )
    return generation


def _generate_and_persist_follows(
    *,
    snapshot: TurnStateSnapshot,
    user_id: str,
    user: UserRecord,
    feed_posts: list[FeedPostView],
    memory_text: str,
    num_followers: int,
    num_follows: int,
    action_config: ActionConfig,
    llm_config: LlmConfig,
    repos: SimulationRepositories,
    conn: sqlite3.Connection,
    trace_ctx: SimulationTraceContext | None = None,
) -> GenerationRecord | None:
    if not action_config.enable_follow_user:
        return None

    candidates = _candidate_users_from_feed(user_id, feed_posts, snapshot.users)
    result = invoke_structured_generation(
        FOLLOW_USERS_PROMPT,
        LlmFollowUserOutput,
        llm_config=llm_config,
        prompt_variables={
            "name": user.name,
            "username": user.username,
            "num_followers": num_followers,
            "num_follows": num_follows,
            "memory": memory_text,
            "candidate_users": _format_candidate_users(candidates),
            "max_follows": action_config.max_follows_per_turn,
        },
        action_type="follow_user",
        user_id=user_id,
        trace_ctx=trace_ctx,
    )
    generation = _persist_generation(
        snapshot, user_id, "follow_user", result, repos, conn
    )
    if result.status == "completed" and isinstance(result.parsed, LlmFollowUserOutput):
        _persist_llm_proposed_actions_follow(
            snapshot,
            user_id,
            generation.generation_id,
            result.parsed.user_ids,
            repos,
            conn,
        )
    return generation


def _generate_and_persist_comments(
    *,
    snapshot: TurnStateSnapshot,
    user_id: str,
    user: UserRecord,
    feed_posts: list[FeedPostView],
    memory_text: str,
    action_config: ActionConfig,
    llm_config: LlmConfig,
    repos: SimulationRepositories,
    conn: sqlite3.Connection,
    trace_ctx: SimulationTraceContext | None = None,
) -> GenerationRecord | None:
    if not action_config.enable_comment_on_post:
        return None

    result = invoke_structured_generation(
        COMMENT_ON_POST_PROMPT,
        LlmCommentOnPostOutput,
        llm_config=llm_config,
        prompt_variables={
            "name": user.name,
            "username": user.username,
            "memory": memory_text,
            "feed_posts": _format_feed_posts(feed_posts),
        },
        action_type="comment_on_post",
        user_id=user_id,
        trace_ctx=trace_ctx,
    )
    generation = _persist_generation(
        snapshot, user_id, "comment_on_post", result, repos, conn
    )
    if result.status == "completed" and isinstance(
        result.parsed, LlmCommentOnPostOutput
    ):
        _persist_llm_proposed_actions_comment(
            snapshot,
            user_id,
            generation.generation_id,
            result.parsed.parent_post_id,
            result.parsed.content,
            repos,
            conn,
        )
    return generation


def _format_feed_posts(feed_posts: list[FeedPostView]) -> str:
    lines: list[str] = []
    for post in feed_posts:
        excerpt = post.content[:120]
        num_likes = post.metadata.get("num_likes", 0)
        lines.append(
            f"{post.post_id} | {post.author_id} | {num_likes} likes | {excerpt}"
        )
    return "\n".join(lines) if lines else "No posts in feed."


def _format_candidate_users(users: list[UserRecord]) -> str:
    lines: list[str] = []
    for user in users:
        lines.append(f"{user.user_id} | @{user.username} | {user.name}")
    return "\n".join(lines) if lines else "No candidate users."


def _follow_counts(user: UserRecord) -> tuple[int, int]:
    profile = user.profile_json or {}
    return (
        int(profile.get("num_followers", 0)),
        int(profile.get("num_follows", 0)),
    )


def _candidate_users_from_feed(
    user_id: str,
    feed_posts: list[FeedPostView],
    users: dict[str, UserRecord],
) -> list[UserRecord]:
    seen: set[str] = set()
    candidates: list[UserRecord] = []
    for post in feed_posts:
        author_id = post.author_id
        if author_id == user_id or author_id in seen:
            continue
        seen.add(author_id)
        author = users.get(author_id)
        if author is not None:
            candidates.append(author)
    return candidates


def _persist_generation(
    snapshot: TurnStateSnapshot,
    user_id: str,
    action_type: ActionType,
    result: LlmGenerationResult,
    repos: SimulationRepositories,
    conn: sqlite3.Connection,
) -> GenerationRecord:
    parsed_json: dict[str, Any] | None = None
    if result.status == "completed" and result.parsed is not None:
        parsed_json = result.parsed.model_dump()

    record = GenerationRecord(
        generation_id=new_generation_id(),
        run_id=snapshot.run_id,
        turn_id=snapshot.turn_id,
        user_id=user_id,
        action_type=action_type,
        parsed_response_json=parsed_json,
        raw_response_json=result.raw_response_json,
        status=result.status,
        latency_ms=result.latency_ms,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        cost_usd=result.cost_usd,
        created_at=get_current_timestamp(),
        error=result.error,
    )
    repos.insert_generation(record, conn)
    return record


def _persist_llm_proposed_actions(
    snapshot: TurnStateSnapshot,
    user_id: str,
    action_type: ActionType,
    generation_id: str,
    post_ids: list[str],
    repos: SimulationRepositories,
    conn: sqlite3.Connection,
) -> None:
    created_at = get_current_timestamp()
    for post_id in post_ids:
        repos.insert_llm_proposed_action(
            LlmProposedActionRecord(
                llm_proposed_action_id=new_llm_proposed_action_id(),
                generation_id=generation_id,
                run_id=snapshot.run_id,
                turn_id=snapshot.turn_id,
                user_id=user_id,
                action_type=action_type,
                target_type="post",
                target_id=post_id,
                created_at=created_at,
            ),
            conn,
        )


def _persist_llm_proposed_actions_write(
    snapshot: TurnStateSnapshot,
    user_id: str,
    generation_id: str,
    content: str,
    repos: SimulationRepositories,
    conn: sqlite3.Connection,
) -> None:
    repos.insert_llm_proposed_action(
        LlmProposedActionRecord(
            llm_proposed_action_id=new_llm_proposed_action_id(),
            generation_id=generation_id,
            run_id=snapshot.run_id,
            turn_id=snapshot.turn_id,
            user_id=user_id,
            action_type="write_post",
            target_type="post",
            target_content=content,
            created_at=get_current_timestamp(),
        ),
        conn,
    )


def _persist_llm_proposed_actions_follow(
    snapshot: TurnStateSnapshot,
    user_id: str,
    generation_id: str,
    followee_ids: list[str],
    repos: SimulationRepositories,
    conn: sqlite3.Connection,
) -> None:
    created_at = get_current_timestamp()
    for followee_id in followee_ids:
        repos.insert_llm_proposed_action(
            LlmProposedActionRecord(
                llm_proposed_action_id=new_llm_proposed_action_id(),
                generation_id=generation_id,
                run_id=snapshot.run_id,
                turn_id=snapshot.turn_id,
                user_id=user_id,
                action_type="follow_user",
                target_type="user",
                target_id=followee_id,
                created_at=created_at,
            ),
            conn,
        )


def _persist_llm_proposed_actions_comment(
    snapshot: TurnStateSnapshot,
    user_id: str,
    generation_id: str,
    parent_post_id: str,
    content: str,
    repos: SimulationRepositories,
    conn: sqlite3.Connection,
) -> None:
    repos.insert_llm_proposed_action(
        LlmProposedActionRecord(
            llm_proposed_action_id=new_llm_proposed_action_id(),
            generation_id=generation_id,
            run_id=snapshot.run_id,
            turn_id=snapshot.turn_id,
            user_id=user_id,
            action_type="comment_on_post",
            target_type="post",
            target_id=parent_post_id,
            target_content=content,
            created_at=get_current_timestamp(),
        ),
        conn,
    )
