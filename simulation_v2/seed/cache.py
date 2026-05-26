"""Disk cache for filtered seed datasets."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from lib.timestamp_utils import get_current_timestamp
from simulation_v2.seed.models import SeedDataset

CACHED_SEED_DATA_DIR = Path(__file__).resolve().parent.parent / "cached_seed_data"
METADATA_FILENAME = "metadata.json"
LOADED_SEED_DATA_FILENAME = "loaded_seed_data.json"


class CachedSeedDataMetadata(BaseModel):
    total_users: int
    total_posts_per_user: int


def _cached_seed_data_dirs() -> list[Path]:
    if not CACHED_SEED_DATA_DIR.is_dir():
        return []
    return sorted(
        (path for path in CACHED_SEED_DATA_DIR.iterdir() if path.is_dir()),
        key=lambda path: path.name,
        reverse=True,
    )


def _read_cached_metadata(cache_dir: Path) -> CachedSeedDataMetadata | None:
    metadata_path = cache_dir / METADATA_FILENAME
    if not metadata_path.is_file():
        return None
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        return CachedSeedDataMetadata.model_validate(payload)
    except (json.JSONDecodeError, ValueError):
        return None


def load_cached_seed_dataset(
    total_users: int,
    total_posts_per_user: int,
) -> SeedDataset | None:
    """Load a matching filtered dataset from disk when available."""
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
            if "likes" not in payload or "follows" not in payload:
                continue
            return SeedDataset.model_validate(payload)
        except (json.JSONDecodeError, ValueError):
            continue

    return None


def save_cached_seed_dataset(
    dataset: SeedDataset,
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
        dataset.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return cache_dir
