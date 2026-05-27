"""Action LLM generation orchestration and persistence."""

from __future__ import annotations

import sqlite3
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
from simulation_v2.config import ActionConfig, LlmConfig
from simulation_v2.db.models import (
    AgentMemoryRecord,
    FeedPostView,
    GeneratedFeedRecord,
    GenerationRecord,
    LlmProposedActionRecord,
    UserRecord,
)
from simulation_v2.db.repositories import SimulationRepositories
from simulation_v2.ids import new_generation_id, new_llm_proposed_action_id
from simulation_v2.lib.decorators import progress_items
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
        memory_text = _format_memory_for_prompt(memory)
        num_followers, num_follows = _follow_counts(user)

        if action_config.enable_like_post:
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
                snapshot,
                user_id,
                "like_post",
                result,
                repos,
                conn,
            )
            generation_records.append(generation)
            if result.status == "completed" and isinstance(
                result.parsed, LlmLikePostOutput
            ):
                _persist_llm_proposed_actions(
                    snapshot,
                    user_id,
                    "like_post",
                    generation.generation_id,
                    result.parsed.post_ids,
                    repos,
                    conn,
                )

        if action_config.enable_write_post:
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
                snapshot,
                user_id,
                "write_post",
                result,
                repos,
                conn,
            )
            generation_records.append(generation)
            if result.status == "completed" and isinstance(
                result.parsed, LlmWritePostOutput
            ):
                _persist_llm_proposed_actions_write(
                    snapshot,
                    user_id,
                    generation.generation_id,
                    result.parsed.content,
                    repos,
                    conn,
                )

        if action_config.enable_follow_user:
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
                snapshot,
                user_id,
                "follow_user",
                result,
                repos,
                conn,
            )
            generation_records.append(generation)
            if result.status == "completed" and isinstance(
                result.parsed, LlmFollowUserOutput
            ):
                _persist_llm_proposed_actions_follow(
                    snapshot,
                    user_id,
                    generation.generation_id,
                    result.parsed.user_ids,
                    repos,
                    conn,
                )

        if action_config.enable_comment_on_post:
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
                snapshot,
                user_id,
                "comment_on_post",
                result,
                repos,
                conn,
            )
            generation_records.append(generation)
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

    return generation_records


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


def _format_memory_for_prompt(memory: AgentMemoryRecord | None) -> str:
    episodic = memory.episodic if memory is not None else ""
    personalized = memory.personalized if memory is not None else ""
    social = memory.social if memory is not None else ""
    return f"""

    Episodic memory: experiences you've had recently
    ```markdown
    {episodic or ""}
    ```

    Personalized profile memory: A list of the agent's interests, liked/disliked topics, posting style, favorite accounts, political/technical/social tendencies and recent mood.

    ```markdown
    {personalized or ""}
    ```

    Social relationships memory: What the agent thinks about other users in the network.

    ```markdown
    {social or ""}
    ```
    """


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
