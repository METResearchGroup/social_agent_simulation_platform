"""Feed generation for simulation turns."""

from __future__ import annotations

import random
from typing import Any

from tqdm import tqdm

from simulation_v2.models.feeds import GeneratedFeedsModel
from simulation_v2.models.turn import TurnInputsModel

FEED_MAX_POSTS = 25
FEED_INCLUDE_PROBABILITY = 0.5

_TQDM_BAR_FORMAT = "{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"


def generate_most_liked_feed(
    user_id: str,
    posts_by_likes_desc: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Build one user's feed from posts ordered by like count descending.

    Skips posts authored by ``user_id``. Each eligible post is included with
    probability ``FEED_INCLUDE_PROBABILITY``. Stops once the feed reaches
    ``FEED_MAX_POSTS`` entries.
    """
    feed: list[dict[str, object]] = []

    for post in posts_by_likes_desc:
        if len(feed) >= FEED_MAX_POSTS:
            break
        if post["user_id"] == user_id:
            continue
        if random.random() < FEED_INCLUDE_PROBABILITY:
            feed.append(post)

    return feed


def generate_most_liked_feeds(
    turn_inputs: TurnInputsModel,
    *,
    show_progress: bool = False,
    turn_number: int | None = None,
) -> GeneratedFeedsModel:
    """Generate a most-liked feed for every user in the turn's seed data."""
    posts_by_likes_desc = sorted(
        (post.model_dump() for post in turn_inputs.seed_data.posts.values()),
        key=lambda post: post["num_likes"],
        reverse=True,
    )

    user_ids = list(turn_inputs.seed_data.users)
    turn_label = turn_number if turn_number is not None else "?"
    user_iter: Any = user_ids
    if show_progress and user_ids:
        user_iter = tqdm(
            user_ids,
            desc=f"Turn {turn_label} (feeds)",
            unit="feed",
            total=len(user_ids),
            leave=False,
            bar_format=_TQDM_BAR_FORMAT,
        )

    feeds_by_user_id: dict[str, list[dict[str, object]]] = {}
    for user_id in user_iter:
        feeds_by_user_id[user_id] = generate_most_liked_feed(
            user_id,
            posts_by_likes_desc,
        )

    return GeneratedFeedsModel(feeds_by_user_id=feeds_by_user_id)


def generate_feeds(
    turn_inputs: TurnInputsModel,
    *,
    show_progress: bool = False,
    turn_number: int | None = None,
) -> GeneratedFeedsModel:
    """Generate feeds for all users in the current turn."""
    return generate_most_liked_feeds(
        turn_inputs,
        show_progress=show_progress,
        turn_number=turn_number,
    )
