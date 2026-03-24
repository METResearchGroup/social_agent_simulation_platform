"""Tests for turn post snapshot models and Post mapping."""

import pytest

from simulation.core.models.posts import PostSource, turn_post_snapshot_to_post
from simulation.core.models.turn_posts import TurnPostSnapshot


class TestTurnPostSnapshot:
    def test_round_trip_fields(self) -> None:
        snap = TurnPostSnapshot(
            turn_post_id="tp_1",
            run_id="run_1",
            turn_number=0,
            author_agent_id="did:plc:author",
            author_handle_at_time="a.bsky.social",
            author_display_name_at_time="A",
            body_text="hello",
            created_at="2026-01-01T00:00:00Z",
            explanation="why",
            model_used="gpt",
            generation_metadata_json="{}",
            generation_created_at="2026-01-01T00:00:01Z",
        )
        assert snap.turn_post_id == "tp_1"
        assert snap.explanation == "why"

    def test_rejects_negative_turn(self) -> None:
        with pytest.raises(ValueError, match="turn_number"):
            TurnPostSnapshot(
                turn_post_id="tp_1",
                run_id="run_1",
                turn_number=-1,
                author_agent_id="did:plc:author",
                author_handle_at_time="a.bsky.social",
                author_display_name_at_time="A",
                body_text="hello",
                created_at="2026-01-01T00:00:00Z",
            )

    def test_turn_post_snapshot_to_post_canonical_identity(self) -> None:
        snap = TurnPostSnapshot(
            turn_post_id="tp_abc",
            run_id="run_1",
            turn_number=1,
            author_agent_id="did:plc:author",
            author_handle_at_time="a.bsky.social",
            author_display_name_at_time="Author",
            body_text="body",
            created_at="2026-01-01T12:00:00Z",
        )
        post = turn_post_snapshot_to_post(snap)
        assert post.post_id == "tp_abc"
        assert post.source is PostSource.SEED_STATE
        assert post.uri == "seed_state:tp_abc"
        assert post.author_agent_id == "did:plc:author"
        assert post.like_count == 0
        assert post.reply_count == 0
