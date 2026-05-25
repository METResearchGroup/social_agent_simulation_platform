"""Load and filter seed data from parquet for simulation runs."""

from __future__ import annotations

import json
from collections import defaultdict
from enum import Enum
from pathlib import Path

from pydantic import BaseModel

from lib.timestamp_utils import get_current_timestamp
from simulation_v2.models.seed_data import (
    FollowModel,
    LoadedPostModel,
    LoadedSeedDataModel,
    LoadedUserModel,
    PostModel,
    SeedDataModel,
    UserModel,
)
from simulation_v2.seed_data import (
    export_seed_data,
    generate_data,
    load_seed_data_from_parquet,
    seed_data_dir_exists,
)

CACHED_SEED_DATA_DIR = Path(__file__).resolve().parent / "cached_seed_data"
METADATA_FILENAME = "metadata.json"
LOADED_SEED_DATA_FILENAME = "loaded_seed_data.json"

_seed_data_cache: SeedDataModel | None = None


class CachedSeedDataMetadata(BaseModel):
    total_users: int
    total_posts_per_user: int


class SeedDataEntity(Enum):
    USERS = "users"
    POSTS = "posts"
    LIKES = "likes"
    FOLLOWS = "follows"


def _get_seed_data() -> SeedDataModel:
    """Return the cached full seed dataset, loading parquet or generating on first access."""
    global _seed_data_cache
    if _seed_data_cache is None:
        if seed_data_dir_exists():
            _seed_data_cache = load_seed_data_from_parquet()
        else:
            _seed_data_cache = generate_data()
            export_seed_data(_seed_data_cache)
    return _seed_data_cache


def clear_seed_data_cache() -> None:
    """Clear the in-memory seed data cache so the next load re-reads parquet."""
    global _seed_data_cache
    _seed_data_cache = None


def _entity_records(entity: SeedDataEntity, seed_data: SeedDataModel) -> list[BaseModel]:
    """Return the list of Pydantic records for the given entity type."""
    if entity == SeedDataEntity.USERS:
        return list(seed_data.users)
    if entity == SeedDataEntity.POSTS:
        return list(seed_data.posts)
    if entity == SeedDataEntity.LIKES:
        return list(seed_data.likes)
    if entity == SeedDataEntity.FOLLOWS:
        return list(seed_data.follows)
    raise ValueError(f"Unsupported entity: {entity}")


def _entity_record_id(entity: SeedDataEntity, record: BaseModel) -> str:
    """Return the canonical string ID used to key a record in entity dicts."""
    if isinstance(record, UserModel):
        return record.user_id
    if isinstance(record, PostModel):
        return record.post_id
    if entity == SeedDataEntity.LIKES:
        assert hasattr(record, "like_id")
        return record.like_id
    if isinstance(record, FollowModel):
        return f"{record.follower_id}:{record.followee_id}"
    raise ValueError(f"Unsupported record type for {entity}: {type(record)}")


def _load_seed_data_entity(entity: SeedDataEntity) -> dict[str, dict]:
    """Load one entity type from cache as a dict keyed by record ID.

    Returns:
        Mapping from entity ID to the record's ``model_dump()`` payload.
    """
    seed_data = _get_seed_data()
    return {
        _entity_record_id(entity, record): record.model_dump()
        for record in _entity_records(entity, seed_data)
    }


def _load_likes() -> tuple[dict[str, dict], dict[str, int]]:
    """Load likes from cache in a single pass.

    Returns:
        A tuple of ``(likes_by_id, likes_by_post_id)`` where ``likes_by_id`` maps
        like ID to the like record dict and ``likes_by_post_id`` maps post ID to
        total like count.
    """
    likes_by_id: dict[str, dict] = {}
    likes_by_post_id: dict[str, int] = defaultdict(int)

    for like in _get_seed_data().likes:
        likes_by_id[like.like_id] = like.model_dump()
        likes_by_post_id[like.post_id] += 1

    return likes_by_id, dict(likes_by_post_id)


def _cached_seed_data_dirs() -> list[Path]:
    """Return cached seed-data directories sorted newest-first by folder name."""
    if not CACHED_SEED_DATA_DIR.is_dir():
        return []
    return sorted(
        (path for path in CACHED_SEED_DATA_DIR.iterdir() if path.is_dir()),
        key=lambda path: path.name,
        reverse=True,
    )


def _read_cached_metadata(cache_dir: Path) -> CachedSeedDataMetadata | None:
    """Read cache metadata when present and valid."""
    metadata_path = cache_dir / METADATA_FILENAME
    if not metadata_path.is_file():
        return None
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        return CachedSeedDataMetadata.model_validate(payload)
    except (json.JSONDecodeError, ValueError):
        return None


def load_cached_seed_data(
    total_users: int,
    total_posts_per_user: int,
) -> LoadedSeedDataModel | None:
    """Load filtered seed data from disk when a matching cache entry exists.

    Scans ``simulation_v2/cached_seed_data/<timestamp>/`` folders, newest first,
    and returns data from the first folder whose ``metadata.json`` matches the
    requested ``total_users`` and ``total_posts_per_user``.

    Args:
        total_users: Requested number of users.
        total_posts_per_user: Requested posts per user.

    Returns:
        Cached seed data when a matching entry exists, otherwise ``None``.
    """
    for cache_dir in _cached_seed_data_dirs():
        metadata = _read_cached_metadata(cache_dir)
        if metadata is None:
            continue
        if (
            metadata.total_users != total_users
            or metadata.total_posts_per_user != total_posts_per_user
        ):
            continue

        data_path = cache_dir / LOADED_SEED_DATA_FILENAME
        if not data_path.is_file():
            continue
        try:
            payload = json.loads(data_path.read_text(encoding="utf-8"))
            return LoadedSeedDataModel.model_validate(payload)
        except (json.JSONDecodeError, ValueError):
            continue

    return None


def _save_cached_seed_data(
    seed_data: LoadedSeedDataModel,
    *,
    total_users: int,
    total_posts_per_user: int,
) -> Path:
    """Persist filtered seed data and metadata under a timestamped cache folder."""
    cache_dir = CACHED_SEED_DATA_DIR / get_current_timestamp()
    cache_dir.mkdir(parents=True, exist_ok=False)

    metadata = CachedSeedDataMetadata(
        total_users=total_users,
        total_posts_per_user=total_posts_per_user,
    )
    (cache_dir / METADATA_FILENAME).write_text(
        metadata.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (cache_dir / LOADED_SEED_DATA_FILENAME).write_text(
        seed_data.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return cache_dir


def _generate_loaded_seed_data(
    total_users: int,
    total_posts_per_user: int,
) -> LoadedSeedDataModel:
    """Generate and filter the in-memory seed dataset for simulation use."""
    users_by_id = _load_seed_data_entity(SeedDataEntity.USERS)
    posts_by_id = _load_seed_data_entity(SeedDataEntity.POSTS)
    follows_by_id = _load_seed_data_entity(SeedDataEntity.FOLLOWS)
    _, likes_by_post_id = _load_likes()

    selected_user_ids = list(users_by_id.keys())[:total_users]
    selected_user_id_set = set(selected_user_ids)

    posts_by_user: dict[str, list[str]] = defaultdict(list)
    for post_id, post in posts_by_id.items():
        user_id = post["user_id"]
        if user_id in selected_user_id_set:
            posts_by_user[user_id].append(post_id)

    selected_post_ids: set[str] = set()
    for user_id in selected_user_ids:
        for post_id in posts_by_user[user_id][:total_posts_per_user]:
            selected_post_ids.add(post_id)

    followers_by_user: dict[str, int] = defaultdict(int)
    follows_by_user: dict[str, int] = defaultdict(int)
    for follow in follows_by_id.values():
        follower_id = follow["follower_id"]
        followee_id = follow["followee_id"]
        if follower_id not in selected_user_id_set:
            continue
        if followee_id not in selected_user_id_set:
            continue
        followers_by_user[followee_id] += 1
        follows_by_user[follower_id] += 1

    loaded_users: dict[str, LoadedUserModel] = {}
    for user_id in selected_user_ids:
        user = users_by_id[user_id]
        loaded_users[user_id] = LoadedUserModel(
            **user,
            num_followers=followers_by_user[user_id],
            num_follows=follows_by_user[user_id],
        )

    loaded_posts: dict[str, LoadedPostModel] = {}
    for post_id in selected_post_ids:
        post = posts_by_id[post_id]
        loaded_posts[post_id] = LoadedPostModel(
            **post,
            num_likes=likes_by_post_id.get(post_id, 0),
        )

    return LoadedSeedDataModel(users=loaded_users, posts=loaded_posts)


def load_seed_data(
    total_users: int,
    total_posts_per_user: int,
    *,
    allow_cached: bool = True,
) -> LoadedSeedDataModel:
    """Load seed data filtered to a simulation-sized subset.

    Selects the first ``total_users`` users, up to ``total_posts_per_user`` posts
    per selected user, and enriches records with aggregate counts:

    - Users receive ``num_followers`` and ``num_follows`` computed from follow
      edges where both endpoints are in the selected user set.
    - Posts receive ``num_likes`` from the global like counts.

    When ``allow_cached`` is true, reuses the newest matching entry under
    ``simulation_v2/cached_seed_data/<timestamp>/`` when available. Otherwise,
    or when no match exists, filters the full dataset loaded from parquet under
    ``simulation_v2/seed_data/`` (generating and exporting parquet first when
    missing) and writes a new filtered cache entry.

    Args:
        total_users: Maximum number of users to include.
        total_posts_per_user: Maximum posts to include per selected user.
        allow_cached: Whether to read from or write to the on-disk cache.

    Returns:
        Filtered users and posts keyed by ``user_id`` and ``post_id``.
    """
    if allow_cached:
        cached = load_cached_seed_data(total_users, total_posts_per_user)
        if cached is not None:
            return cached

    loaded = _generate_loaded_seed_data(total_users, total_posts_per_user)
    if allow_cached:
        _save_cached_seed_data(
            loaded,
            total_users=total_users,
            total_posts_per_user=total_posts_per_user,
        )
    return loaded


if __name__ == "__main__":
    subset = load_seed_data(total_users=10, total_posts_per_user=5)
    print(f"Loaded {len(subset.users)} users and {len(subset.posts)} posts")
    sample_user_id = next(iter(subset.users))
    sample_user = subset.users[sample_user_id]
    print(
        f"Sample user {sample_user.username}: "
        f"{sample_user.num_followers} followers, {sample_user.num_follows} following"
    )
    sample_post_id = next(iter(subset.posts))
    sample_post = subset.posts[sample_post_id]
    print(
        f"Sample post by {sample_post.user_id[:8]}...: "
        f"{sample_post.num_likes} likes, content={sample_post.content[:60]}..."
    )
