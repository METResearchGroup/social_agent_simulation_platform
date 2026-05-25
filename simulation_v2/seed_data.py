"""Generates and loads seed data.

To run:

PYTHONPATH=. uv run python simulation_v2/seed_data.py
"""

from __future__ import annotations

import os
import random
import statistics
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from faker import Faker

from lib.timestamp_utils import CREATED_AT_FORMAT
from simulation_v2.models.seed_data import (
    FollowModel,
    LikeModel,
    PostModel,
    SeedDataModel,
    UserModel,
)

SEED_DATA_PATH = str(Path(__file__).resolve().parent / "seed_data")

NUM_USERS = 5_000
MAX_POSTS = 1_000_000
MAX_LIKES = 1_500_000
MAX_FOLLOWS = 30_000
FOLLOW_PROBABILITY = 0.001

POST_COUNT_MEAN = 100
POST_COUNT_SD = 5
LIKE_COUNT_MEAN = 200
LIKE_COUNT_SD = 5

THREE_DAYS_AGO = datetime.now(timezone.utc) - timedelta(days=3)
ONE_MONTH_AGO = datetime.now(timezone.utc) - timedelta(days=30)
SIX_MONTHS_AGO = datetime.now(timezone.utc) - timedelta(days=180)


def _format_timestamp(value: datetime) -> str:
    """Format a datetime as a UTC timestamp string using ``CREATED_AT_FORMAT``."""
    return value.astimezone(timezone.utc).strftime(CREATED_AT_FORMAT)


def _parse_timestamp(value: str) -> datetime:
    """Parse a ``CREATED_AT_FORMAT`` timestamp string into a UTC datetime."""
    parsed = datetime.strptime(value, CREATED_AT_FORMAT)
    return parsed.replace(tzinfo=timezone.utc)


def _sample_timestamp_between(start: datetime, end: datetime) -> datetime | None:
    """Sample a uniform random UTC datetime in ``[start, end)``.

    Returns:
        ``None`` when ``start >= end`` (invalid or empty window).
    """
    if start >= end:
        return None
    offset_seconds = random.uniform(0, (end - start).total_seconds())
    return start + timedelta(seconds=offset_seconds)


def _sample_created_at_between(start: datetime, end: datetime) -> str | None:
    """Sample a formatted created-at timestamp uniformly in ``[start, end)``."""
    sampled = _sample_timestamp_between(start, end)
    if sampled is None:
        return None
    return _format_timestamp(sampled)


def _clamp_normal(mean: float, sd: float) -> int:
    """Draw from a normal distribution and clamp the result to a minimum of 0."""
    return max(0, int(random.gauss(mean, sd)))


def generate_users(*, fake: Faker | None = None, num_users: int = NUM_USERS) -> list[UserModel]:
    """Generate fake users with Faker.

    Each user's ``created_at`` is sampled uniformly between six months and one
    month ago.

    Args:
        fake: Optional shared Faker instance for deterministic generation.
        num_users: Number of users to create.

    Returns:
        Generated user records.
    """
    faker = fake or Faker()
    users: list[UserModel] = []
    for _ in range(num_users):
        created_at = _sample_created_at_between(SIX_MONTHS_AGO, ONE_MONTH_AGO)
        if created_at is None:
            created_at = _format_timestamp(ONE_MONTH_AGO)
        users.append(
            UserModel(
                user_id=faker.uuid4(),
                name=faker.name(),
                email=faker.email(),
                username=faker.user_name(),
                created_at=created_at,
            )
        )
    return users


def generate_posts(
    users: list[UserModel],
    *,
    fake: Faker | None = None,
    max_posts: int = MAX_POSTS,
) -> list[PostModel]:
    """Generate fake posts for the given users.

    Each user receives a post count drawn from ``Normal(POST_COUNT_MEAN,
    POST_COUNT_SD)``, clamped to at least 0. Post ``created_at`` values are
    sampled between the user's creation time and three days ago.

    Args:
        users: Users who may author posts.
        fake: Optional shared Faker instance for deterministic generation.
        max_posts: Global cap on total generated posts.

    Returns:
        Generated post records.
    """
    faker = fake or Faker()
    posts: list[PostModel] = []
    for user in users:
        if len(posts) >= max_posts:
            break

        num_posts = _clamp_normal(POST_COUNT_MEAN, POST_COUNT_SD)
        remaining = max_posts - len(posts)
        num_posts = min(num_posts, remaining)
        user_created_at = _parse_timestamp(user.created_at)

        for _ in range(num_posts):
            created_at = _sample_created_at_between(user_created_at, THREE_DAYS_AGO)
            if created_at is None:
                continue
            posts.append(
                PostModel(
                    post_id=faker.uuid4(),
                    user_id=user.user_id,
                    content=faker.paragraph(nb_sentences=3),
                    created_at=created_at,
                )
            )
    return posts


def _sample_posts_without_replacement(
    posts: list[PostModel],
    *,
    author_id: str,
    sample_size: int,
) -> list[PostModel]:
    """Sample posts without replacement, excluding posts authored by ``author_id``."""
    if sample_size == 0 or not posts:
        return []

    selected: list[PostModel] = []
    selected_post_ids: set[str] = set()
    max_attempts = sample_size * 20 + 100
    attempts = 0

    while len(selected) < sample_size and attempts < max_attempts:
        candidate = posts[random.randrange(len(posts))]
        if candidate.user_id == author_id or candidate.post_id in selected_post_ids:
            attempts += 1
            continue
        selected.append(candidate)
        selected_post_ids.add(candidate.post_id)
        attempts += 1

    return selected


def generate_likes(
    users: list[UserModel],
    posts: list[PostModel],
    *,
    fake: Faker | None = None,
    max_likes: int = MAX_LIKES,
) -> list[LikeModel]:
    """Generate like records for users on posts they did not author.

    Each user likes a count drawn from ``Normal(LIKE_COUNT_MEAN, LIKE_COUNT_SD)``,
    clamped to at least 0. Like ``created_at`` values fall between the later of
    the user and post creation times and three days ago. Likes with invalid time
    windows are skipped.

    Args:
        users: Users who may create likes.
        posts: Candidate posts to like.
        fake: Optional shared Faker instance for deterministic generation.
        max_likes: Global cap on total generated likes.

    Returns:
        Generated like records with globally unique ``like_id`` values.
    """
    if not posts:
        return []

    faker = fake or Faker()
    likes: list[LikeModel] = []
    used_like_ids: set[str] = set()

    for user in users:
        if len(likes) >= max_likes:
            break

        num_likes = _clamp_normal(LIKE_COUNT_MEAN, LIKE_COUNT_SD)
        remaining = max_likes - len(likes)
        num_likes = min(num_likes, remaining)

        sampled_posts = _sample_posts_without_replacement(
            posts,
            author_id=user.user_id,
            sample_size=num_likes,
        )
        if not sampled_posts:
            continue

        user_created_at = _parse_timestamp(user.created_at)
        for post in sampled_posts:
            if len(likes) >= max_likes:
                break

            post_created_at = _parse_timestamp(post.created_at)
            window_start = max(user_created_at, post_created_at)
            created_at = _sample_created_at_between(window_start, THREE_DAYS_AGO)
            if created_at is None:
                continue

            like_id = faker.uuid4()
            while like_id in used_like_ids:
                like_id = faker.uuid4()
            used_like_ids.add(like_id)

            likes.append(
                LikeModel(
                    like_id=like_id,
                    user_id=user.user_id,
                    post_id=post.post_id,
                    created_at=created_at,
                )
            )

    return likes


def generate_follows(
    users: list[UserModel],
    *,
    max_follows: int = MAX_FOLLOWS,
    follow_probability: float = FOLLOW_PROBABILITY,
) -> list[FollowModel]:
    """Generate directed follow edges between distinct users.

    Uses an ``O(n^2)`` loop over user pairs. Each pair creates a follow edge with
    fixed probability ``follow_probability``. Edges are deduplicated and generation
    stops once ``max_follows`` edges have been created.

    Args:
        users: Users who may follow or be followed.
        max_follows: Global cap on total generated follow edges.
        follow_probability: Probability of creating a follow for each user pair.

    Returns:
        Generated follow records.
    """
    follow_pairs: set[tuple[str, str]] = set()

    for follower in users:
        if len(follow_pairs) >= max_follows:
            break
        for followee in users:
            if len(follow_pairs) >= max_follows:
                break
            if follower.user_id == followee.user_id:
                continue
            if random.random() < follow_probability:
                follow_pairs.add((follower.user_id, followee.user_id))

    return [
        FollowModel(follower_id=follower_id, followee_id=followee_id)
        for follower_id, followee_id in follow_pairs
    ]


def generate_data(*, fake: Faker | None = None) -> SeedDataModel:
    """Generate the full seed dataset: users, posts, likes, and follows.

    Args:
        fake: Optional shared Faker instance for deterministic generation.

    Returns:
        Combined seed data model containing all generated entities.
    """
    faker = fake or Faker()
    users = generate_users(fake=faker)
    posts = generate_posts(users, fake=faker)
    likes = generate_likes(users, posts, fake=faker)
    follows = generate_follows(users)
    return SeedDataModel(users=users, posts=posts, likes=likes, follows=follows)


def export_seed_data(seed_data: SeedDataModel) -> None:
    """Persist generated seed data to disk.

    Currently a no-op placeholder until parquet export is implemented.
    """
    pass


def _distribution_stats(values: list[int]) -> dict[str, float | int]:
    """Compute descriptive statistics for a list of integer counts."""
    if not values:
        return {"count": 0}
    return {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "stdev": statistics.pstdev(values) if len(values) > 1 else 0.0,
    }


def print_seed_data_statistics(seed_data: SeedDataModel) -> None:
    """Print record totals and per-user distribution stats for seed data."""
    posts_by_user: dict[str, int] = defaultdict(int)
    for post in seed_data.posts:
        posts_by_user[post.user_id] += 1

    likes_by_user: dict[str, int] = defaultdict(int)
    for like in seed_data.likes:
        likes_by_user[like.user_id] += 1

    followers_by_user: dict[str, int] = defaultdict(int)
    following_by_user: dict[str, int] = defaultdict(int)
    for follow in seed_data.follows:
        followers_by_user[follow.followee_id] += 1
        following_by_user[follow.follower_id] += 1

    posts_per_user = [posts_by_user[user.user_id] for user in seed_data.users]
    likes_per_user = [likes_by_user[user.user_id] for user in seed_data.users]
    followers_per_user = [followers_by_user[user.user_id] for user in seed_data.users]
    following_per_user = [following_by_user[user.user_id] for user in seed_data.users]

    print("=== Seed data totals ===")
    print(f"users:   {len(seed_data.users):>10,}")
    print(f"posts:   {len(seed_data.posts):>10,}")
    print(f"likes:   {len(seed_data.likes):>10,}")
    print(f"follows: {len(seed_data.follows):>10,}")
    print(f"total records: {len(seed_data.users) + len(seed_data.posts) + len(seed_data.likes) + len(seed_data.follows):>10,}")

    print("\n=== Posts per user ===")
    for key, value in _distribution_stats(posts_per_user).items():
        if isinstance(value, float):
            print(f"{key}: {value:,.2f}")
        else:
            print(f"{key}: {value:,}")

    print("\n=== Likes per user ===")
    for key, value in _distribution_stats(likes_per_user).items():
        if isinstance(value, float):
            print(f"{key}: {value:,.2f}")
        else:
            print(f"{key}: {value:,}")

    print("\n=== Followers per user ===")
    for key, value in _distribution_stats(followers_per_user).items():
        if isinstance(value, float):
            print(f"{key}: {value:,.2f}")
        else:
            print(f"{key}: {value:,}")

    print("\n=== Following per user ===")
    for key, value in _distribution_stats(following_per_user).items():
        if isinstance(value, float):
            print(f"{key}: {value:,.2f}")
        else:
            print(f"{key}: {value:,}")


if __name__ == "__main__":
    if not os.path.exists(SEED_DATA_PATH):
        seed_data: SeedDataModel = generate_data()
        export_seed_data(seed_data)
        print_seed_data_statistics(seed_data)
