"""Tests for feed validators and snapshot helpers."""

from __future__ import annotations

import pytest

from simulation_v2.config import LocalSimulationConfig
from simulation_v2.db.models import FeedPostView, PostRecord
from simulation_v2.feeds.interfaces import (
    get_feed_generator,
    hydrate_feed_post_view,
    post_like_counts,
)
from simulation_v2.feeds.validators import FeedValidationError, validate_feed
from simulation_v2.worker.state import TurnStateSnapshot
from tests.simulation_v2.db import factories

FIXED_TS = "2026-01-01T00:00:00.000000+00:00"


def _view(*, post_id: str, author_id: str) -> FeedPostView:
    return FeedPostView(
        post_id=post_id,
        author_id=author_id,
        content="hello",
        created_at=FIXED_TS,
        metadata={"num_likes": 0},
    )


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
        "posts": {},
        "likes": [],
        "follows": [],
        "comments": [],
        "agent_memories": {},
        "prior_generated_feeds": [],
    }
    defaults.update(overrides)
    return TurnStateSnapshot.model_validate(defaults)


class TestValidateFeed:
    def test_empty_feed_passes(self) -> None:
        validate_feed("u1", [])

    def test_duplicate_post_id_raises(self) -> None:
        views = [
            _view(post_id="p1", author_id="u2"),
            _view(post_id="p1", author_id="u2"),
        ]
        with pytest.raises(FeedValidationError, match="duplicate post_id"):
            validate_feed("u1", views)

    def test_self_authored_post_raises(self) -> None:
        views = [_view(post_id="p1", author_id="u1")]
        with pytest.raises(FeedValidationError, match="self-authored"):
            validate_feed("u1", views)


class TestPostLikeCounts:
    def test_counts_likes_by_post_id(self) -> None:
        run_id = "run-1"
        snapshot = _snapshot(
            likes=[
                factories.LikeRecordFactory.create(
                    run_id=run_id, post_id="p1", author_id="u2"
                ),
                factories.LikeRecordFactory.create(
                    run_id=run_id, post_id="p1", author_id="u3"
                ),
                factories.LikeRecordFactory.create(
                    run_id=run_id, post_id="p2", author_id="u1"
                ),
            ]
        )

        assert post_like_counts(snapshot) == {"p1": 2, "p2": 1}


class TestHydrateFeedPostView:
    def test_hydrates_metadata_with_like_count(self) -> None:
        post = PostRecord(
            post_id="p1",
            run_id="run-1",
            author_id="u2",
            content="hello",
            created_at=FIXED_TS,
            created_at_turn=0,
            metadata_json={"num_likes": 3},
        )

        view = hydrate_feed_post_view(post, like_count=5)

        assert view.post_id == "p1"
        assert view.author_id == "u2"
        assert view.metadata["num_likes"] == 5


class TestGetFeedGenerator:
    def test_unknown_algorithm_raises(self) -> None:
        with pytest.raises(ValueError, match="unknown feed algorithm"):
            get_feed_generator("invalid")

    @pytest.mark.parametrize("algorithm", ["most_liked", "reverse_chronological"])
    def test_known_algorithms_resolve(self, algorithm: str) -> None:
        generator = get_feed_generator(algorithm)
        assert generator.name == algorithm
