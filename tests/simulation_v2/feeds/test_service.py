"""Integration tests for feed generation and persistence."""

from __future__ import annotations

from pathlib import Path

from simulation_v2.config import FeedConfig, LocalSimulationConfig
from simulation_v2.db.connection import transaction
from simulation_v2.db.database import SimulationDatabase
from simulation_v2.feeds.service import generate_and_persist_feeds
from simulation_v2.models.seed_data import LoadedPostModel, LoadedUserModel
from simulation_v2.seed.loader import persist_seed_for_run
from simulation_v2.seed.models import SeedDataset
from simulation_v2.worker.state import load_turn_snapshot
from tests.simulation_v2.db import factories

FIXED_TS = "2026-01-01T00:00:00.000000+00:00"


def _tiny_dataset() -> SeedDataset:
    return SeedDataset(
        users={
            "u1": LoadedUserModel(
                user_id="u1",
                name="Alice",
                email="a@example.com",
                username="alice",
                created_at=FIXED_TS,
                num_followers=0,
                num_follows=0,
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
        likes={},
        follows={},
    )


class TestGenerateAndPersistFeeds:
    def test_persists_one_feed_per_user(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.sqlite3"
        db = SimulationDatabase(db_path)
        db.initialize()
        config = LocalSimulationConfig.default().model_copy(
            update={"feed": FeedConfig(include_probability=1.0, max_posts=10)}
        )
        run = factories.RunRecordFactory.create(
            config_json=config.model_dump(mode="json"),
            seed_metadata_json=None,
        )
        dataset = _tiny_dataset()

        with transaction(db_path) as conn:
            db.repos.insert_run(run, conn)
            persist_seed_for_run(run.run_id, dataset, db.repos, conn)
            turn = factories.TurnRecordFactory.create(
                run_id=run.run_id,
                turn_number=1,
                status="pending",
            )
            db.repos.insert_turn(turn, conn)
            snapshot = load_turn_snapshot(run.run_id, turn.turn_id, db.repos, conn)
            records = generate_and_persist_feeds(
                snapshot,
                config.feed,
                db.repos,
                conn,
            )

        assert len(records) == 2
        assert {record.user_id for record in records} == {"u1", "u2"}
        assert all(record.algorithm == "most_liked" for record in records)
        assert all(
            record.feed_post_ids == [view.post_id for view in record.feed_posts]
            for record in records
        )

        with transaction(db_path) as conn:
            loaded = db.repos.list_generated_feeds_for_run(run.run_id, conn)

        assert len(loaded) == 2
        by_user = {feed.user_id: feed for feed in loaded}
        assert by_user["u1"].feed_post_ids == ["p2"]
        assert by_user["u2"].feed_post_ids == ["p1"]
