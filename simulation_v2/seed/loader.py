"""Load, filter, and persist seed data for simulation runs."""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from enum import Enum

from pydantic import BaseModel

from simulation_v2.config import LocalSimulationConfig, SeedConfig
from simulation_v2.db.models import (
    AgentMemoryRecord,
    FollowRecord,
    LikeRecord,
    PostRecord,
    UserRecord,
)
from simulation_v2.db.repositories import SimulationRepositories
from simulation_v2.ids import new_follow_id
from simulation_v2.models.seed_data import (
    FollowModel,
    LikeModel,
    LoadedPostModel,
    LoadedUserModel,
    PostModel,
    SeedDataModel,
    UserModel,
)
from simulation_v2.seed import cache as seed_cache
from simulation_v2.seed.generator import (
    export_seed_data,
    generate_data,
    load_seed_data_from_parquet,
    seed_data_dir_exists,
)
from simulation_v2.seed.models import SeedDataset, SeedImportSummary
from simulation_v2.time import get_current_timestamp

_seed_data_cache: SeedDataModel | None = None


class SeedDataEntity(Enum):
    USERS = "users"
    POSTS = "posts"
    LIKES = "likes"
    FOLLOWS = "follows"


def clear_seed_data_cache() -> None:
    """Clear the in-memory full seed dataset cache."""
    global _seed_data_cache
    _seed_data_cache = None


def _get_seed_data() -> SeedDataModel:
    global _seed_data_cache
    if _seed_data_cache is None:
        if seed_data_dir_exists():
            _seed_data_cache = load_seed_data_from_parquet()
        else:
            _seed_data_cache = generate_data()
            export_seed_data(_seed_data_cache)
    return _seed_data_cache


def _entity_records(
    entity: SeedDataEntity, seed_data: SeedDataModel
) -> list[BaseModel]:
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
    if isinstance(record, UserModel):
        return record.user_id
    if isinstance(record, PostModel):
        return record.post_id
    if isinstance(record, LikeModel):
        return record.like_id
    if isinstance(record, FollowModel):
        return f"{record.follower_id}:{record.followee_id}"
    raise ValueError(f"Unsupported record type for {entity}: {type(record)}")


def _load_seed_data_entity(entity: SeedDataEntity) -> dict[str, dict]:
    seed_data = _get_seed_data()
    return {
        _entity_record_id(entity, record): record.model_dump()
        for record in _entity_records(entity, seed_data)
    }


def _load_likes() -> tuple[dict[str, dict], dict[str, int]]:
    likes_by_id: dict[str, dict] = {}
    likes_by_post_id: dict[str, int] = defaultdict(int)

    for like in _get_seed_data().likes:
        likes_by_id[like.like_id] = like.model_dump()
        likes_by_post_id[like.post_id] += 1

    return likes_by_id, dict(likes_by_post_id)


def _generate_seed_dataset(
    total_users: int,
    total_posts_per_user: int,
) -> SeedDataset:
    users_by_id = _load_seed_data_entity(SeedDataEntity.USERS)
    posts_by_id = _load_seed_data_entity(SeedDataEntity.POSTS)
    likes_by_id = _load_seed_data_entity(SeedDataEntity.LIKES)
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

    selected_likes: dict[str, LikeModel] = {}
    for like_id, like in likes_by_id.items():
        if like["user_id"] not in selected_user_id_set:
            continue
        if like["post_id"] not in selected_post_ids:
            continue
        selected_likes[like_id] = LikeModel.model_validate(like)

    selected_follows: dict[str, FollowModel] = {}
    followers_by_user: dict[str, int] = defaultdict(int)
    follows_by_user: dict[str, int] = defaultdict(int)
    for follow_key, follow in follows_by_id.items():
        follower_id = follow["follower_id"]
        followee_id = follow["followee_id"]
        if follower_id not in selected_user_id_set:
            continue
        if followee_id not in selected_user_id_set:
            continue
        selected_follows[follow_key] = FollowModel.model_validate(follow)
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

    return SeedDataset(
        users=loaded_users,
        posts=loaded_posts,
        likes=selected_likes,
        follows=selected_follows,
    )


def load_seed_dataset(
    seed: SeedConfig,
    *,
    allow_cached: bool = True,
) -> SeedDataset:
    """Load seed data filtered to a simulation-sized subset."""
    if allow_cached:
        cached = seed_cache.load_cached_seed_dataset(
            seed.total_users, seed.total_posts_per_user
        )
        if cached is not None:
            return cached

    dataset = _generate_seed_dataset(seed.total_users, seed.total_posts_per_user)
    if allow_cached:
        seed_cache.save_cached_seed_dataset(
            dataset,
            total_users=seed.total_users,
            total_posts_per_user=seed.total_posts_per_user,
        )
    return dataset


def persist_seed_for_run(
    run_id: str,
    dataset: SeedDataset,
    repos: SimulationRepositories,
    conn: sqlite3.Connection,
) -> SeedImportSummary:
    """Insert seed entities for a run in FK-safe order."""
    for user in dataset.users.values():
        repos.insert_user(
            UserRecord(
                user_id=user.user_id,
                run_id=run_id,
                name=user.name,
                email=user.email,
                username=user.username,
                profile_json={
                    "num_followers": user.num_followers,
                    "num_follows": user.num_follows,
                },
                created_at=user.created_at,
            ),
            conn,
        )

    for post in dataset.posts.values():
        repos.insert_post(
            PostRecord(
                post_id=post.post_id,
                run_id=run_id,
                author_id=post.user_id,
                content=post.content,
                created_at=post.created_at,
                created_at_turn=0,
                metadata_json={"num_likes": post.num_likes},
            ),
            conn,
        )

    for like in dataset.likes.values():
        repos.insert_like(
            LikeRecord(
                like_id=like.like_id,
                run_id=run_id,
                post_id=like.post_id,
                author_id=like.user_id,
                created_at=like.created_at,
                created_at_turn=0,
            ),
            conn,
        )

    for follow in dataset.follows.values():
        repos.insert_follow(
            FollowRecord(
                follow_id=new_follow_id(),
                run_id=run_id,
                follower_id=follow.follower_id,
                followee_id=follow.followee_id,
                created_at=get_current_timestamp(),
                created_at_turn=0,
            ),
            conn,
        )

    for user in dataset.users.values():
        repos.insert_agent_memory(
            AgentMemoryRecord(
                run_id=run_id,
                user_id=user.user_id,
                preferences_json={
                    "name": user.name,
                    "username": user.username,
                    "email": user.email,
                    "num_followers": user.num_followers,
                    "num_follows": user.num_follows,
                },
                episodic="",
                personalized="",
                social="",
                updated_at=get_current_timestamp(),
            ),
            conn,
        )

    return SeedImportSummary(
        user_count=len(dataset.users),
        post_count=len(dataset.posts),
        like_count=len(dataset.likes),
        follow_count=len(dataset.follows),
        memory_count=len(dataset.users),
    )


def import_seed_if_needed(
    run_id: str,
    config: LocalSimulationConfig,
    repos: SimulationRepositories,
    conn: sqlite3.Connection,
) -> SeedImportSummary | None:
    """Import seed data once per run; skip when metadata already set."""
    run = repos.get_run(run_id, conn)
    if run is None:
        raise ValueError(f"Run not found: {run_id}")
    if run.seed_metadata_json is not None:
        return None

    dataset = load_seed_dataset(config.seed)
    summary = persist_seed_for_run(run_id, dataset, repos, conn)
    repos.update_run_seed_metadata(
        run_id,
        {
            "user_count": summary.user_count,
            "post_count": summary.post_count,
            "like_count": summary.like_count,
            "follow_count": summary.follow_count,
            "memory_count": summary.memory_count,
            "total_users": config.seed.total_users,
            "total_posts_per_user": config.seed.total_posts_per_user,
        },
        conn,
    )
    return summary
