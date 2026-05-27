"""Unit tests for simulation_v2 seed loader."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from simulation_v2.config import LocalSimulationConfig, SeedConfig
from simulation_v2.db.connection import transaction
from simulation_v2.db.database import SimulationDatabase
from simulation_v2.seed.loader import (
    import_seed_if_needed,
    load_seed_dataset,
    persist_seed_for_run,
)
from simulation_v2.seed.models import (
    FollowModel,
    LikeModel,
    LoadedPostModel,
    LoadedUserModel,
    SeedDataset,
    SeedImportSummary,
)
from tests.simulation_v2.db import factories

FIXED_TS = "2026-01-01T00:00:00.000000+00:00"


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "test.sqlite3"
    SimulationDatabase(path).initialize()
    return path


def _tiny_dataset() -> SeedDataset:
    return SeedDataset(
        users={
            "u1": LoadedUserModel(
                user_id="u1",
                name="Alice",
                email="a@example.com",
                username="alice",
                created_at=FIXED_TS,
                num_followers=1,
                num_follows=1,
            ),
            "u2": LoadedUserModel(
                user_id="u2",
                name="Bob",
                email="b@example.com",
                username="bob",
                created_at=FIXED_TS,
                num_followers=0,
                num_follows=0,
            ),
        },
        posts={
            "p1": LoadedPostModel(
                post_id="p1",
                user_id="u1",
                content="hello",
                created_at=FIXED_TS,
                num_likes=1,
            ),
            "p2": LoadedPostModel(
                post_id="p2",
                user_id="u2",
                content="world",
                created_at=FIXED_TS,
                num_likes=0,
            ),
        },
        likes={
            "l1": LikeModel(
                like_id="l1",
                user_id="u2",
                post_id="p1",
                created_at=FIXED_TS,
            ),
        },
        follows={
            "u1:u2": FollowModel(follower_id="u1", followee_id="u2"),
        },
    )


class TestLoadSeedDataset:
    def test_load_seed_dataset_respects_config_subset(self) -> None:
        dataset = load_seed_dataset(
            SeedConfig(total_users=3, total_posts_per_user=5),
            allow_cached=False,
        )
        assert len(dataset.users) == 3
        assert len(dataset.posts) == 15

    def test_load_seed_dataset_includes_likes_and_follows_when_present(self) -> None:
        dataset = load_seed_dataset(
            SeedConfig(total_users=50, total_posts_per_user=5),
            allow_cached=False,
        )
        assert len(dataset.likes) > 0
        assert len(dataset.follows) > 0


class TestPersistSeedForRun:
    def test_persist_seed_for_run_writes_all_entity_types(self, db_path: Path) -> None:
        run = factories.RunRecordFactory.create(seed_metadata_json=None)
        db = SimulationDatabase(db_path)
        dataset = _tiny_dataset()

        with transaction(db_path) as conn:
            db.repos.insert_run(run, conn)
            summary = persist_seed_for_run(run.run_id, dataset, db.repos, conn)
            counts = db.repos.count_seed_entities_for_run(run.run_id, conn)

        assert summary == SeedImportSummary(
            user_count=2,
            post_count=2,
            like_count=1,
            follow_count=1,
            memory_count=2,
        )
        assert counts["user_count"] == 2
        assert counts["post_count"] == 2
        assert counts["like_count"] == 1
        assert counts["follow_count"] == 1
        assert counts["memory_count"] == 2


class TestImportSeedIfNeeded:
    def test_import_seed_if_needed_is_idempotent(self, db_path: Path) -> None:
        config = LocalSimulationConfig.default().model_copy(
            update={"seed": SeedConfig(total_users=2, total_posts_per_user=1)}
        )
        run = factories.RunRecordFactory.create(
            config_json=config.model_dump(mode="json"),
            seed_metadata_json=None,
        )
        db = SimulationDatabase(db_path)
        dataset = _tiny_dataset()

        with patch(
            "simulation_v2.seed.loader.load_seed_dataset",
            return_value=dataset,
        ):
            with transaction(db_path) as conn:
                db.repos.insert_run(run, conn)
                first = import_seed_if_needed(run.run_id, config, db.repos, conn)
                second = import_seed_if_needed(run.run_id, config, db.repos, conn)
                counts = db.repos.count_seed_entities_for_run(run.run_id, conn)

        assert first is not None
        assert second is None
        assert counts["user_count"] == 2
        assert counts["post_count"] == 2

    def test_import_seed_if_needed_skips_when_metadata_set(self, db_path: Path) -> None:
        config = LocalSimulationConfig.default()
        run = factories.RunRecordFactory.create(
            config_json=config.model_dump(mode="json"),
            seed_metadata_json={"user_count": 0},
        )
        db = SimulationDatabase(db_path)

        with patch(
            "simulation_v2.seed.loader.load_seed_dataset",
        ) as mock_load:
            with transaction(db_path) as conn:
                db.repos.insert_run(run, conn)
                result = import_seed_if_needed(run.run_id, config, db.repos, conn)
                counts = db.repos.count_seed_entities_for_run(run.run_id, conn)

        assert result is None
        mock_load.assert_not_called()
        assert counts["user_count"] == 0
