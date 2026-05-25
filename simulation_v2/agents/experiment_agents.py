"""Manual experiment script for simulation v2 agent actions.

Run:

PYTHONPATH=. uv run python simulation_v2/agents/experiment_agents.py
"""

from __future__ import annotations

import json
from typing import Any

from simulation_v2.agent import (
    MAX_POSTS_TO_LIKE_PER_TURN,
    MAX_USERS_TO_FOLLOW_PER_TURN,
    _user_to_dict,
)
from simulation_v2.agents.actions import (
    propose_follow_users,
    propose_like_posts,
    propose_write_post,
)
from simulation_v2.models.actions import AgentTurnActions
from simulation_v2.models.seed_data import LoadedUserModel


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
    }


def _build_mock_feeds() -> dict[str, list[dict[str, Any]]]:
    return {
        "user-alice": [
            {
                "post_id": "post-1",
                "user_id": "user-bob",
                "content": "Just shipped a new feature for our feed ranking experiment.",
                "created_at": "2026_02_01-10:00:00",
                "num_likes": 42,
            },
            {
                "post_id": "post-2",
                "user_id": "user-bob",
                "content": "Anyone else excited about lightweight agent simulators?",
                "created_at": "2026_02_01-11:00:00",
                "num_likes": 17,
            },
        ],
        "user-bob": [
            {
                "post_id": "post-3",
                "user_id": "user-alice",
                "content": "Running load tests on the new simulation engine today.",
                "created_at": "2026_02_01-09:30:00",
                "num_likes": 31,
            },
            {
                "post_id": "post-4",
                "user_id": "user-alice",
                "content": "Coffee + pydantic models = productive morning.",
                "created_at": "2026_02_01-12:15:00",
                "num_likes": 8,
            },
        ],
    }


def main() -> dict[str, AgentTurnActions]:
    """Run a sample of each agent action type against simple mock data."""
    users = _build_mock_users()
    feeds = _build_mock_feeds()
    results: dict[str, AgentTurnActions] = {}

    for user_id, user in users.items():
        user_dict = _user_to_dict(user)
        feed = feeds[user_id]
        print(f"\n=== Actions for {user.name} (@{user.username}) ===")
        print(f"Feed posts: {[post['post_id'] for post in feed]}")

        likes = propose_like_posts(
            user_dict,
            feed,
            max_likes=MAX_POSTS_TO_LIKE_PER_TURN,
        )
        print(f"\nLikes ({len(likes)}):")
        print(json.dumps([like.model_dump() for like in likes], indent=2))

        posts = [propose_write_post(user_dict, feed)]
        print(f"\nPosts ({len(posts)}):")
        print(json.dumps([post.model_dump() for post in posts], indent=2))

        author_ids = {
            post["user_id"]
            for post in feed
            if post.get("user_id") and post["user_id"] != user_id
        }
        candidate_users = [
            _user_to_dict(users[author_id])
            for author_id in author_ids
            if author_id in users
        ]
        follows = propose_follow_users(
            user_dict,
            candidate_users,
            max_follows=MAX_USERS_TO_FOLLOW_PER_TURN,
        )
        print(f"\nFollows ({len(follows)}):")
        print(json.dumps([follow.model_dump() for follow in follows], indent=2))

        results[user_id] = AgentTurnActions(
            likes=likes,
            posts=posts,
            follows=follows,
        )

    return results


if __name__ == "__main__":
    main()
