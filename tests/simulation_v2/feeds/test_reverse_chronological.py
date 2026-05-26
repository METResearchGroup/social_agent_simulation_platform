"""Tests for the reverse_chronological feed plugin."""

from __future__ import annotations

from simulation_v2.config import FeedConfig, LocalSimulationConfig
from simulation_v2.feeds.reverse_chronological import ReverseChronologicalFeedGenerator
from simulation_v2.worker.state import TurnStateSnapshot
from tests.simulation_v2.db import factories

FIXED_TS = "2026-01-01T00:00:00.000000+00:00"
FIXED_TS_2 = "2026-01-02T00:00:00.000000+00:00"


def _snapshot(**overrides: object) -> TurnStateSnapshot:
    run_id = "run-1"
    defaults = {
        "run_id": run_id,
        "turn_id": "turn-1",
        "turn_number": 1,
        "config": LocalSimulationConfig.default(),
        "users": {
            "u1": factories.UserRecordFactory.create(user_id="u1", run_id=run_id),
            "u2": factories.UserRecordFactory.create(user_id="u2", run_id=run_id),
        },
        "posts": {
            "p2": factories.PostRecordFactory.create(
                post_id="p2",
                run_id=run_id,
                author_id="u2",
                content="older tie b",
                created_at=FIXED_TS,
            ),
            "p1": factories.PostRecordFactory.create(
                post_id="p1",
                run_id=run_id,
                author_id="u2",
                content="older tie a",
                created_at=FIXED_TS,
            ),
            "p3": factories.PostRecordFactory.create(
                post_id="p3",
                run_id=run_id,
                author_id="u2",
                content="newest",
                created_at=FIXED_TS_2,
            ),
            "p4": factories.PostRecordFactory.create(
                post_id="p4",
                run_id=run_id,
                author_id="u1",
                content="self",
                created_at=FIXED_TS_2,
            ),
        },
        "likes": [],
        "follows": [],
        "comments": [],
        "agent_memories": {},
        "prior_generated_feeds": [],
    }
    defaults.update(overrides)
    return TurnStateSnapshot.model_validate(defaults)


class TestReverseChronologicalFeedGenerator:
    def test_sorts_by_created_at_desc_with_post_id_tiebreak(self) -> None:
        snapshot = _snapshot()
        config = FeedConfig(max_posts=10)
        generator = ReverseChronologicalFeedGenerator()

        feed = generator.generate(snapshot, "u1", config)

        assert [view.post_id for view in feed] == ["p3", "p1", "p2"]

    def test_excludes_self_posts_and_respects_max_posts(self) -> None:
        snapshot = _snapshot()
        config = FeedConfig(max_posts=1)
        generator = ReverseChronologicalFeedGenerator()

        feed = generator.generate(snapshot, "u1", config)

        assert len(feed) == 1
        assert feed[0].post_id == "p3"
        assert feed[0].author_id != "u1"
