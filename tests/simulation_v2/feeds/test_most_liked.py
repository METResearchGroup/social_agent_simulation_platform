"""Tests for the most_liked feed plugin."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from simulation_v2.config import FeedConfig, LocalSimulationConfig
from simulation_v2.feeds.most_liked import MostLikedFeedGenerator
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
            "u3": factories.UserRecordFactory.create(user_id="u3", run_id=run_id),
        },
        "posts": {
            "p1": factories.PostRecordFactory.create(
                post_id="p1",
                run_id=run_id,
                author_id="u1",
                content="from u1",
                created_at=FIXED_TS,
            ),
            "p2": factories.PostRecordFactory.create(
                post_id="p2",
                run_id=run_id,
                author_id="u2",
                content="from u2",
                created_at=FIXED_TS,
            ),
            "p3": factories.PostRecordFactory.create(
                post_id="p3",
                run_id=run_id,
                author_id="u3",
                content="from u3",
                created_at=FIXED_TS_2,
            ),
        },
        "likes": [
            factories.LikeRecordFactory.create(
                run_id=run_id, post_id="p2", author_id="u1"
            ),
            factories.LikeRecordFactory.create(
                run_id=run_id, post_id="p2", author_id="u3"
            ),
            factories.LikeRecordFactory.create(
                run_id=run_id, post_id="p3", author_id="u1"
            ),
        ],
        "follows": [],
        "comments": [],
        "agent_memories": {},
        "prior_generated_feeds": [],
    }
    defaults.update(overrides)
    return TurnStateSnapshot.model_validate(defaults)


class TestMostLikedFeedGenerator:
    def test_excludes_self_posts_and_orders_by_likes(self) -> None:
        snapshot = _snapshot()
        config = FeedConfig(include_probability=1.0, max_posts=10)
        generator = MostLikedFeedGenerator()

        feed = generator.generate(snapshot, "u1", config)

        assert [view.post_id for view in feed] == ["p2", "p3"]
        assert all(view.author_id != "u1" for view in feed)
        assert feed[0].metadata["num_likes"] == 2
        assert feed[1].metadata["num_likes"] == 1

    def test_respects_max_posts(self) -> None:
        snapshot = _snapshot()
        config = FeedConfig(include_probability=1.0, max_posts=1)
        generator = MostLikedFeedGenerator()

        feed = generator.generate(snapshot, "u1", config)

        assert len(feed) == 1
        assert feed[0].post_id == "p2"

    @patch("simulation_v2.feeds.most_liked.random.random", return_value=1.0)
    def test_include_probability_gate_excludes_post(
        self, mock_random: MagicMock
    ) -> None:
        assert mock_random.return_value == 1.0
        snapshot = _snapshot()
        config = FeedConfig(include_probability=0.5, max_posts=10)
        generator = MostLikedFeedGenerator()

        feed = generator.generate(snapshot, "u1", config)

        assert feed == []
