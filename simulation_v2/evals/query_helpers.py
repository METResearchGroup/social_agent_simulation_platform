"""Scope-aware SQLite read helpers for eval plugins."""

from __future__ import annotations

from collections import defaultdict

from simulation_v2.db.models import (
    GeneratedFeedRecord,
    GenerationRecord,
    ProposedActionRecord,
    UserRecord,
)
from simulation_v2.evals.interfaces import EvalContext

CANONICAL_ACTION_TYPES = (
    "like_post",
    "write_post",
    "follow_user",
    "comment_on_post",
)


def load_proposed_actions(context: EvalContext) -> list[ProposedActionRecord]:
    if context.scope == "turn":
        if context.turn_id is None:
            return []
        return context.repos.list_proposed_actions_for_turn(
            context.run_id, context.turn_id, context.conn
        )
    actions: list[ProposedActionRecord] = []
    for turn in context.repos.list_turns_for_run(context.run_id, context.conn):
        actions.extend(
            context.repos.list_proposed_actions_for_turn(
                context.run_id, turn.turn_id, context.conn
            )
        )
    return actions


def load_generations(context: EvalContext) -> list[GenerationRecord]:
    if context.scope == "turn":
        if context.turn_id is None:
            return []
        return context.repos.list_generations_for_turn(
            context.run_id, context.turn_id, context.conn
        )
    generations: list[GenerationRecord] = []
    for turn in context.repos.list_turns_for_run(context.run_id, context.conn):
        generations.extend(
            context.repos.list_generations_for_turn(
                context.run_id, turn.turn_id, context.conn
            )
        )
    return generations


def load_feeds_for_scope(context: EvalContext) -> list[GeneratedFeedRecord]:
    feeds = context.repos.list_generated_feeds_for_run(context.run_id, context.conn)
    if context.scope == "turn":
        if context.turn_id is None:
            return []
        return [feed for feed in feeds if feed.turn_id == context.turn_id]
    return feeds


def load_users(context: EvalContext) -> list[UserRecord]:
    return context.repos.list_users_for_run(context.run_id, context.conn)


def count_executed_by_action_type(context: EvalContext) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    turn_number = context.turn_number

    for like in context.repos.list_likes_for_run(context.run_id, context.conn):
        if _matches_turn_scope(like.created_at_turn, turn_number, context.scope):
            counts["like_post"] += 1

    for follow in context.repos.list_follows_for_run(context.run_id, context.conn):
        if _matches_turn_scope(follow.created_at_turn, turn_number, context.scope):
            counts["follow_user"] += 1

    for post in context.repos.list_posts_for_run(context.run_id, context.conn):
        if post.created_at_turn == 0:
            continue
        if _matches_turn_scope(post.created_at_turn, turn_number, context.scope):
            counts["write_post"] += 1

    for comment in context.repos.list_comments_for_run(context.run_id, context.conn):
        if _matches_turn_scope(comment.created_at_turn, turn_number, context.scope):
            counts["comment_on_post"] += 1

    return dict(counts)


def _matches_turn_scope(
    created_at_turn: int, turn_number: int | None, scope: str
) -> bool:
    if scope == "run":
        return created_at_turn > 0
    if turn_number is None:
        return False
    return created_at_turn == turn_number
