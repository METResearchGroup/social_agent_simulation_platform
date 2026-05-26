"""Unit tests for feed Pydantic models."""

from __future__ import annotations

from simulation_v2.db.models import FeedPostView, GeneratedFeedRecord
from simulation_v2.time import get_current_timestamp


class TestFeedModels:
    def test_feed_post_view_round_trip(self) -> None:
        view = FeedPostView(
            post_id="p1",
            author_id="u1",
            content="hello",
            created_at=get_current_timestamp(),
            metadata={"likes": 3},
        )

        assert FeedPostView.model_validate(view.model_dump()) == view

    def test_generated_feed_record_round_trip(self) -> None:
        view = FeedPostView(
            post_id="p1",
            author_id="u1",
            content="hello",
            created_at=get_current_timestamp(),
        )
        record = GeneratedFeedRecord(
            feed_id="feed-1",
            run_id="run-1",
            turn_id="turn-1",
            user_id="u1",
            algorithm="most_liked",
            feed_post_ids=["p1"],
            feed_posts=[view],
            created_at=get_current_timestamp(),
        )

        assert GeneratedFeedRecord.model_validate(record.model_dump()) == record
