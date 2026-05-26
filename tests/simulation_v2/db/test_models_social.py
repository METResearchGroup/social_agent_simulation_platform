"""Unit tests for seed/social entity Pydantic models."""

from __future__ import annotations

from simulation_v2.db.models import (
    CommentRecord,
    FollowRecord,
    LikeRecord,
    PostRecord,
    UserRecord,
)
from simulation_v2.time import get_current_timestamp


class TestSocialModels:
    def test_user_record_round_trip(self) -> None:
        record = UserRecord(
            user_id="u1",
            run_id="run-1",
            name="Alice",
            email="alice@example.com",
            username="alice",
            profile_json={"bio": "hello"},
            created_at=get_current_timestamp(),
        )

        assert UserRecord.model_validate(record.model_dump()) == record

    def test_post_record_round_trip(self) -> None:
        record = PostRecord(
            post_id="p1",
            run_id="run-1",
            author_id="u1",
            content="hello world",
            created_at=get_current_timestamp(),
            created_at_turn=0,
            metadata_json={"source": "seed"},
        )

        assert PostRecord.model_validate(record.model_dump()) == record

    def test_like_record_round_trip(self) -> None:
        record = LikeRecord(
            like_id="l1",
            run_id="run-1",
            post_id="p1",
            author_id="u1",
            created_at=get_current_timestamp(),
            created_at_turn=1,
        )

        assert LikeRecord.model_validate(record.model_dump()) == record

    def test_follow_record_round_trip(self) -> None:
        record = FollowRecord(
            follow_id="f1",
            run_id="run-1",
            follower_id="u1",
            followee_id="u2",
            created_at=get_current_timestamp(),
            created_at_turn=1,
        )

        assert FollowRecord.model_validate(record.model_dump()) == record

    def test_comment_record_round_trip(self) -> None:
        record = CommentRecord(
            comment_id="c1",
            run_id="run-1",
            parent_post_id="p1",
            author_id="u1",
            content="nice post",
            created_at=get_current_timestamp(),
            created_at_turn=1,
        )

        assert CommentRecord.model_validate(record.model_dump()) == record
