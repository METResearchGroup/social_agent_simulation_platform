"""Integration tests for like, comment, and follow action repositories.

Uses a real SQLite database. Requires a run to exist for FK (run_id).
"""

from __future__ import annotations

import sqlite3

import pytest

from lib.agent_id import canonical_agent_id
from tests.factories import (
    CommentFactory,
    FollowFactory,
    GeneratedCommentFactory,
    GeneratedFollowFactory,
    GeneratedLikeFactory,
    GenerationMetadataFactory,
    LikeFactory,
    RunConfigFactory,
)


@pytest.fixture
def seed_action_agents(temp_db: str) -> None:
    """Insert minimal agent rows so action adapters can resolve handles to canonical ids."""
    conn = sqlite3.connect(temp_db)
    try:
        for handle in (
            "alice.bsky.social",
            "bob.bsky.social",
            "charlie.bsky.social",
        ):
            aid = canonical_agent_id(handle)
            conn.execute(
                """
                INSERT OR IGNORE INTO agent (
                    agent_id, handle, persona_source, display_name, created_at, updated_at
                ) VALUES (?, ?, 'test', ?, '2026-01-01', '2026-01-01')
                """,
                (aid, handle, handle),
            )
        conn.commit()
    finally:
        conn.close()


def _make_run(run_repo) -> str:
    """Create a run and return run_id."""
    config = RunConfigFactory.create(
        num_agents=1, num_turns=2, feed_algorithm="chronological"
    )
    run = run_repo.create_run(config)
    return run.run_id


class TestSQLiteLikeRepositoryIntegration:
    """Integration tests for LikeRepository."""

    def test_write_and_read_likes_by_run_turn(
        self, seed_action_agents, run_repo, like_repo
    ) -> None:
        """write_likes then read_likes_by_run_turn round-trips."""
        run_id = _make_run(run_repo)
        turn_number = 0

        alice_id = canonical_agent_id("alice.bsky.social")
        likes = [
            GeneratedLikeFactory.create(
                like=LikeFactory.create(
                    like_id="like_1",
                    agent_id=alice_id,
                    post_id="at://did:plc:post1",
                    created_at="2026-02-24T12:00:00Z",
                ),
                explanation="Great post",
                metadata=GenerationMetadataFactory.create(
                    model_used=None,
                    generation_metadata=None,
                    created_at="2026-02-24T12:00:00Z",
                ),
            )
        ]
        like_repo.write_likes(run_id, turn_number, likes)

        result = like_repo.read_likes_by_run_turn(run_id, turn_number)
        assert len(result) == 1
        assert result[0].like_id == "like_1"
        assert result[0].agent_id == alice_id
        assert result[0].post_id == "at://did:plc:post1"
        assert result[0].run_id == run_id
        assert result[0].turn_number == turn_number

    def test_read_likes_empty_when_none_persisted(self, run_repo, like_repo) -> None:
        """read_likes_by_run_turn returns empty list when no likes for that turn."""
        run_id = _make_run(run_repo)
        result = like_repo.read_likes_by_run_turn(run_id, 0)
        assert result == []


class TestSQLiteCommentRepositoryIntegration:
    """Integration tests for CommentRepository."""

    def test_write_and_read_comments_by_run_turn(
        self, seed_action_agents, run_repo, comment_repo
    ) -> None:
        """write_comments then read_comments_by_run_turn round-trips."""
        run_id = _make_run(run_repo)
        turn_number = 0

        bob_id = canonical_agent_id("bob.bsky.social")
        comments = [
            GeneratedCommentFactory.create(
                comment=CommentFactory.create(
                    comment_id="comment_1",
                    agent_id=bob_id,
                    post_id="at://did:plc:post2",
                    text="Nice one!",
                    created_at="2026-02-24T12:01:00Z",
                ),
                explanation="Relevant",
                metadata=GenerationMetadataFactory.create(
                    model_used=None,
                    generation_metadata=None,
                    created_at="2026-02-24T12:01:00Z",
                ),
            )
        ]
        comment_repo.write_comments(run_id, turn_number, comments)

        result = comment_repo.read_comments_by_run_turn(run_id, turn_number)
        assert len(result) == 1
        assert result[0].comment_id == "comment_1"
        assert result[0].agent_id == bob_id
        assert result[0].post_id == "at://did:plc:post2"
        assert result[0].text == "Nice one!"
        assert result[0].run_id == run_id
        assert result[0].turn_number == turn_number


class TestSQLiteFollowRepositoryIntegration:
    """Integration tests for FollowRepository."""

    def test_write_and_read_follows_by_run_turn(
        self, seed_action_agents, run_repo, follow_repo
    ) -> None:
        """write_follows then read_follows_by_run_turn round-trips."""
        run_id = _make_run(run_repo)
        turn_number = 0

        alice_id = canonical_agent_id("alice.bsky.social")
        charlie_id = canonical_agent_id("charlie.bsky.social")
        follows = [
            GeneratedFollowFactory.create(
                follow=FollowFactory.create(
                    follow_id="follow_1",
                    agent_id=alice_id,
                    target_agent_id=charlie_id,
                    created_at="2026-02-24T12:02:00Z",
                ),
                explanation="Interesting account",
                metadata=GenerationMetadataFactory.create(
                    model_used=None,
                    generation_metadata=None,
                    created_at="2026-02-24T12:02:00Z",
                ),
            )
        ]
        follow_repo.write_follows(run_id, turn_number, follows)

        result = follow_repo.read_follows_by_run_turn(run_id, turn_number)
        assert len(result) == 1
        assert result[0].follow_id == "follow_1"
        assert result[0].agent_id == alice_id
        assert result[0].target_agent_id == charlie_id
        assert result[0].run_id == run_id
        assert result[0].turn_number == turn_number
