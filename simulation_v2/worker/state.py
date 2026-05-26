"""Turn snapshot loading from SQLite-backed run state."""

from __future__ import annotations

import sqlite3

from pydantic import BaseModel, Field

from simulation_v2.config import LocalSimulationConfig
from simulation_v2.db.errors import RunNotFoundError, TurnNotFoundError
from simulation_v2.db.models import (
    AgentMemoryRecord,
    CommentRecord,
    FollowRecord,
    GeneratedFeedRecord,
    LikeRecord,
    MemoryDiffRecord,
    PostRecord,
    UserRecord,
)
from simulation_v2.db.repositories import SimulationRepositories


class TurnStateSnapshot(BaseModel):
    run_id: str
    turn_id: str
    turn_number: int
    config: LocalSimulationConfig
    users: dict[str, UserRecord]
    posts: dict[str, PostRecord]
    likes: list[LikeRecord]
    follows: list[FollowRecord]
    comments: list[CommentRecord]
    agent_memories: dict[str, AgentMemoryRecord]
    prior_generated_feeds: list[GeneratedFeedRecord]


class PendingTurnDiffs(BaseModel):
    posts: list[PostRecord] = Field(default_factory=list)
    likes: list[LikeRecord] = Field(default_factory=list)
    follows: list[FollowRecord] = Field(default_factory=list)
    comments: list[CommentRecord] = Field(default_factory=list)
    memory_diffs: list[MemoryDiffRecord] = Field(default_factory=list)


def load_turn_snapshot(
    run_id: str,
    turn_id: str,
    repos: SimulationRepositories,
    conn: sqlite3.Connection,
) -> TurnStateSnapshot:
    turn = repos.get_turn(turn_id, conn)
    if turn is None:
        raise TurnNotFoundError(turn_id)
    if turn.run_id != run_id:
        raise ValueError(
            f"turn {turn_id!r} belongs to run {turn.run_id!r}, not {run_id!r}"
        )

    run = repos.get_run(run_id, conn)
    if run is None:
        raise RunNotFoundError(run_id)
    config = LocalSimulationConfig.model_validate(run.config_json)

    users = {user.user_id: user for user in repos.list_users_for_run(run_id, conn)}
    all_posts = repos.list_posts_for_run(run_id, conn)
    posts = {
        post.post_id: post
        for post in all_posts
        if post.created_at_turn < turn.turn_number
    }
    likes = [
        like
        for like in repos.list_likes_for_run(run_id, conn)
        if like.created_at_turn < turn.turn_number
    ]
    follows = [
        follow
        for follow in repos.list_follows_for_run(run_id, conn)
        if follow.created_at_turn < turn.turn_number
    ]
    comments = [
        comment
        for comment in repos.list_comments_for_run(run_id, conn)
        if comment.created_at_turn < turn.turn_number
    ]
    agent_memories = {
        memory.user_id: memory
        for memory in repos.list_agent_memories_for_run(run_id, conn)
    }

    turn_number_by_id = {
        prior_turn.turn_id: prior_turn.turn_number
        for prior_turn in repos.list_turns_for_run(run_id, conn)
    }
    prior_generated_feeds = [
        feed
        for feed in repos.list_generated_feeds_for_run(run_id, conn)
        if turn_number_by_id.get(feed.turn_id, 0) < turn.turn_number
    ]

    return TurnStateSnapshot(
        run_id=run_id,
        turn_id=turn_id,
        turn_number=turn.turn_number,
        config=config,
        users=users,
        posts=posts,
        likes=likes,
        follows=follows,
        comments=comments,
        agent_memories=agent_memories,
        prior_generated_feeds=prior_generated_feeds,
    )
