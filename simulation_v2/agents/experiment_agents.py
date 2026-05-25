"""Manual experiment script for simulation v2 agent actions.

Run:

PYTHONPATH=. uv run python simulation_v2/agents/experiment_agents.py

Verify Opik traces in project ``simulation_engine_v2`` (tag ``metrics_summary`` for
turn summary). Set ``OPIK_DISABLED=1`` to skip Opik export.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from simulation_v2.agents.actions import get_agent_actions
from simulation_v2.logging_config import configure_simulation_logging
from simulation_v2.models.actions import AgentTurnActions
from simulation_v2.models.seed_data import LoadedUserModel
from simulation_v2.telemetry.context import SimulationTraceContext
from simulation_v2.telemetry.opik import (
    configure_opik,
    flush_opik,
    is_opik_enabled,
    log_turn_llm_summary_to_opik,
)
from simulation_v2.telemetry.simulation_metrics import log_turn_simulation_metrics

configure_simulation_logging()


def _build_mock_users() -> dict[str, LoadedUserModel]:
    return {
        "user-alice": LoadedUserModel(
            user_id="user-alice",
            name="Alice Chen",
            email="alice@example.com",
            username="alice",
            created_at="2026_01_01-12:00:00",
            num_followers=120,
            num_follows=85,
        ),
        "user-bob": LoadedUserModel(
            user_id="user-bob",
            name="Bob Rivera",
            email="bob@example.com",
            username="bob",
            created_at="2026_01_02-12:00:00",
            num_followers=45,
            num_follows=60,
        ),
        "user-carol": LoadedUserModel(
            user_id="user-carol",
            name="Carol Nguyen",
            email="carol@example.com",
            username="carol",
            created_at="2026_01_03-12:00:00",
            num_followers=210,
            num_follows=140,
        ),
        "user-dave": LoadedUserModel(
            user_id="user-dave",
            name="Dave Patel",
            email="dave@example.com",
            username="dave",
            created_at="2026_01_04-12:00:00",
            num_followers=18,
            num_follows=22,
        ),
        "user-eve": LoadedUserModel(
            user_id="user-eve",
            name="Eve Martinez",
            email="eve@example.com",
            username="eve",
            created_at="2026_01_05-12:00:00",
            num_followers=330,
            num_follows=95,
        ),
    }


def _build_mock_posts() -> list[dict[str, Any]]:
    authors = [
        ("user-alice", "Alice"),
        ("user-bob", "Bob"),
        ("user-carol", "Carol"),
        ("user-dave", "Dave"),
        ("user-eve", "Eve"),
    ]
    posts: list[dict[str, Any]] = []
    post_index = 1
    for author_id, author_name in authors:
        for slot in range(4):
            posts.append(
                {
                    "post_id": f"post-{post_index}",
                    "user_id": author_id,
                    "content": (
                        f"{author_name} post {slot + 1}: sharing updates from the "
                        f"simulation engine experiment."
                    ),
                    "created_at": f"2026_02_0{1 + slot}-10:00:00",
                    "num_likes": (post_index * 7) % 53,
                }
            )
            post_index += 1
    return posts


def _build_mock_feeds(
    users: dict[str, LoadedUserModel],
    posts: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    feeds: dict[str, list[dict[str, Any]]] = {}
    for user_id in users:
        feed = [post for post in posts if post["user_id"] != user_id]
        feed.sort(key=lambda post: post.get("num_likes", 0), reverse=True)
        feeds[user_id] = feed
    return feeds


def main() -> dict[str, AgentTurnActions]:
    """Run agent actions for five users against twenty mock posts."""
    configure_opik()
    run_id = str(uuid.uuid4())
    trace_ctx = SimulationTraceContext(
        run_id=run_id,
        turn_number=1,
        enabled=is_opik_enabled(),
    )

    users = _build_mock_users()
    posts = _build_mock_posts()
    feeds = _build_mock_feeds(users, posts)
    results: dict[str, AgentTurnActions] = {}

    for user_id, user in users.items():
        feed = feeds[user_id]
        print(f"\n=== Actions for {user.name} (@{user.username}) ===")
        print(f"Feed posts ({len(feed)}): {[post['post_id'] for post in feed]}")

        actions = get_agent_actions(
            user,
            feed,
            users,
            trace_ctx=trace_ctx,
        )
        print(f"\nLikes ({len(actions.likes)}):")
        print(json.dumps([like.model_dump() for like in actions.likes], indent=2))
        print(f"\nPosts ({len(actions.posts)}):")
        print(json.dumps([post.model_dump() for post in actions.posts], indent=2))
        print(f"\nFollows ({len(actions.follows)}):")
        print(json.dumps([follow.model_dump() for follow in actions.follows], indent=2))
        results[user_id] = actions

    turn_summary = trace_ctx.turn_llm_collector.summarize(
        run_id=run_id,
        turn_number=1,
    )
    log_turn_llm_summary_to_opik(turn_summary)
    log_turn_simulation_metrics(
        trace_ctx.simulation_metrics,
        run_id=run_id,
        turn_number=1,
    )
    flush_opik()

    print(
        f"\nTelemetry summary run_id={run_id} "
        f"total_llm_requests={turn_summary.overall.request_count} "
        f"like_posts={turn_summary.by_action['like_posts'].request_count} "
        f"write_post={turn_summary.by_action['write_post'].request_count} "
        f"follow_users={turn_summary.by_action['follow_users'].request_count}"
    )
    return results


if __name__ == "__main__":
    main()
