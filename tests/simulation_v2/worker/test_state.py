"""Tests for turn snapshot loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from simulation_v2.config import LocalSimulationConfig
from simulation_v2.db.connection import transaction
from simulation_v2.db.database import SimulationDatabase
from simulation_v2.models.seed_data import (
    FollowModel,
    LikeModel,
    LoadedPostModel,
    LoadedUserModel,
)
from simulation_v2.seed.loader import persist_seed_for_run
from simulation_v2.seed.models import SeedDataset
from simulation_v2.worker.state import load_turn_snapshot
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


def _make_turn(*, run_id: str, turn_number: int):
    return factories.TurnRecordFactory.create(
        run_id=run_id,
        turn_number=turn_number,
        status="pending",
    )


class TestLoadTurnSnapshot:
    def test_turn_one_snapshot_matches_seed_entities(self, db_path: Path) -> None:
        config = LocalSimulationConfig.default()
        run = factories.RunRecordFactory.create(
            config_json=config.model_dump(mode="json"),
            seed_metadata_json=None,
        )
        db = SimulationDatabase(db_path)
        dataset = _tiny_dataset()

        with transaction(db_path) as conn:
            db.repos.insert_run(run, conn)
            persist_seed_for_run(run.run_id, dataset, db.repos, conn)
            turn = _make_turn(run_id=run.run_id, turn_number=1)
            db.repos.insert_turn(turn, conn)
            turn_id = turn.turn_id

        with transaction(db_path) as conn:
            snapshot = load_turn_snapshot(run.run_id, turn_id, db.repos, conn)

        assert snapshot.run_id == run.run_id
        assert snapshot.turn_id == turn_id
        assert snapshot.turn_number == 1
        assert len(snapshot.users) == 2
        assert len(snapshot.posts) == 2
        assert len(snapshot.likes) == 1
        assert len(snapshot.follows) == 1
        assert len(snapshot.agent_memories) == 2
        assert snapshot.prior_generated_feeds == []

    def test_turn_two_excludes_current_turn_entities(self, db_path: Path) -> None:
        config = LocalSimulationConfig.default()
        run = factories.RunRecordFactory.create(
            config_json=config.model_dump(mode="json"),
            seed_metadata_json=None,
        )
        db = SimulationDatabase(db_path)
        dataset = _tiny_dataset()
        turn_one_post = factories.PostRecordFactory.create(
            run_id=run.run_id,
            post_id="turn1-post",
            author_id="u1",
            created_at_turn=1,
        )
        turn_two_post = factories.PostRecordFactory.create(
            run_id=run.run_id,
            post_id="turn2-post",
            author_id="u1",
            created_at_turn=2,
        )

        with transaction(db_path) as conn:
            db.repos.insert_run(run, conn)
            persist_seed_for_run(run.run_id, dataset, db.repos, conn)
            db.repos.insert_post(turn_one_post, conn)
            db.repos.insert_post(turn_two_post, conn)
            turn = _make_turn(run_id=run.run_id, turn_number=2)
            db.repos.insert_turn(turn, conn)
            turn_id = turn.turn_id

        with transaction(db_path) as conn:
            snapshot = load_turn_snapshot(run.run_id, turn_id, db.repos, conn)

        post_ids = set(snapshot.posts)
        assert "p1" in post_ids
        assert "p2" in post_ids
        assert "turn1-post" in post_ids
        assert "turn2-post" not in post_ids

    def test_agent_memories_include_one_record_per_user(self, db_path: Path) -> None:
        config = LocalSimulationConfig.default()
        run = factories.RunRecordFactory.create(
            config_json=config.model_dump(mode="json"),
            seed_metadata_json=None,
        )
        db = SimulationDatabase(db_path)

        with transaction(db_path) as conn:
            db.repos.insert_run(run, conn)
            persist_seed_for_run(run.run_id, _tiny_dataset(), db.repos, conn)
            turn = _make_turn(run_id=run.run_id, turn_number=1)
            db.repos.insert_turn(turn, conn)
            turn_id = turn.turn_id

        with transaction(db_path) as conn:
            snapshot = load_turn_snapshot(run.run_id, turn_id, db.repos, conn)

        assert set(snapshot.agent_memories) == {"u1", "u2"}
