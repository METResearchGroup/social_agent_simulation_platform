"""Integration tests for validate_and_persist_proposed_actions."""

from __future__ import annotations

from pathlib import Path

from simulation_v2.actions.service import validate_and_persist_proposed_actions
from simulation_v2.config import ActionConfig, FeedConfig, LocalSimulationConfig
from simulation_v2.db.connection import transaction
from simulation_v2.db.database import SimulationDatabase
from simulation_v2.db.models import FeedPostView, GeneratedFeedRecord
from simulation_v2.ids import new_feed_id
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


class TestValidateAndPersistProposedActions:
    def test_persists_validated_and_rejected_rows(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.sqlite3"
        db = SimulationDatabase(db_path)
        db.initialize()
        config = LocalSimulationConfig.default().model_copy(
            update={
                "feed": FeedConfig(include_probability=1.0, max_posts=10),
                "action": ActionConfig(
                    enable_like_post=True,
                    enable_write_post=False,
                    enable_follow_user=False,
                    enable_comment_on_post=False,
                    max_likes_per_turn=5,
                ),
            }
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
            feed_records = [
                GeneratedFeedRecord(
                    feed_id=new_feed_id(),
                    run_id=run.run_id,
                    turn_id=turn.turn_id,
                    user_id="u1",
                    algorithm="test",
                    feed_post_ids=["p1", "p2"],
                    feed_posts=[
                        FeedPostView(
                            post_id="p1",
                            author_id="u1",
                            content="hello",
                            created_at=FIXED_TS,
                        ),
                        FeedPostView(
                            post_id="p2",
                            author_id="u2",
                            content="world",
                            created_at=FIXED_TS,
                        ),
                    ],
                    created_at=FIXED_TS,
                )
            ]

            generation = factories.GenerationRecordFactory.create(
                run_id=run.run_id,
                turn_id=turn.turn_id,
                user_id="u1",
                action_type="like_post",
            )
            db.repos.insert_generation(generation, conn)

            valid_like = factories.LlmProposedActionRecordFactory.create(
                run_id=run.run_id,
                turn_id=turn.turn_id,
                user_id="u1",
                generation_id=generation.generation_id,
                action_type="like_post",
                target_type="post",
                target_id="p2",
                created_at="2026-01-01T00:00:01+00:00",
            )
            self_like = factories.LlmProposedActionRecordFactory.create(
                run_id=run.run_id,
                turn_id=turn.turn_id,
                user_id="u1",
                generation_id=generation.generation_id,
                action_type="like_post",
                target_type="post",
                target_id="p1",
                created_at="2026-01-01T00:00:02+00:00",
            )
            db.repos.insert_llm_proposed_action(valid_like, conn)
            db.repos.insert_llm_proposed_action(self_like, conn)

            proposed = validate_and_persist_proposed_actions(
                snapshot,
                feed_records,
                config.action,
                db.repos,
                conn,
            )

        assert len(proposed) == 2
        assert proposed[0].record_kind == "validated"
        assert proposed[0].target_id == "p2"
        assert proposed[0].filter_id is None
        assert proposed[1].record_kind == "rejected"
        assert proposed[1].target_id == "p1"
        assert proposed[1].filter_id == "no_self_like"
        assert proposed[1].rejection_stage == "business_rules"

        with transaction(db_path) as conn:
            loaded = db.repos.list_proposed_actions_for_turn(
                run.run_id, turn.turn_id, conn
            )

        assert len(loaded) == 2
        assert loaded[0].record_kind == "validated"
        assert loaded[1].record_kind == "rejected"

    def test_returns_empty_when_no_llm_rows(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.sqlite3"
        db = SimulationDatabase(db_path)
        db.initialize()
        config = LocalSimulationConfig.default()
        run = factories.RunRecordFactory.create(
            config_json=config.model_dump(mode="json"),
            seed_metadata_json=None,
        )

        with transaction(db_path) as conn:
            db.repos.insert_run(run, conn)
            turn = factories.TurnRecordFactory.create(run_id=run.run_id, turn_number=1)
            db.repos.insert_turn(turn, conn)
            snapshot = load_turn_snapshot(run.run_id, turn.turn_id, db.repos, conn)
            feed_records: list[GeneratedFeedRecord] = [
                GeneratedFeedRecord(
                    feed_id=new_feed_id(),
                    run_id=run.run_id,
                    turn_id=turn.turn_id,
                    user_id="u1",
                    algorithm="chronological",
                    feed_post_ids=[],
                    feed_posts=[],
                    created_at=FIXED_TS,
                )
            ]
            proposed = validate_and_persist_proposed_actions(
                snapshot,
                feed_records,
                config.action,
                db.repos,
                conn,
            )

        assert proposed == []
