"""Integration tests for like, comment, and follow action repositories.

Uses a real SQLite database. Requires a run to exist for FK (run_id).
"""

from __future__ import annotations

import json
import sqlite3

import pytest

from db.adapters.sqlite.turn_parent import TURN_PARENT_PLACEHOLDER_CREATED_AT
from lib.agent_id import canonical_agent_id
from simulation.core.models.actions import TurnAction
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
    """Insert minimal agent rows so action writes satisfy FK to ``agent``."""
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


def _seed_turn_parent_row(temp_db: str, run_id: str, turn_number: int) -> None:
    """Ensure ``turns`` has a parent row so ``turn_*`` action FK checks pass."""
    conn = sqlite3.connect(temp_db)
    try:
        conn.execute(
            """
            INSERT OR IGNORE INTO turns (run_id, turn_number, total_actions, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                run_id,
                turn_number,
                json.dumps({k.value: 0 for k in TurnAction}),
                TURN_PARENT_PLACEHOLDER_CREATED_AT,
            ),
        )
        conn.commit()
    finally:
        conn.close()


_ALLOWED_ACTION_TABLES = frozenset({"turn_likes", "turn_comments", "turn_follows"})


def _count_rows(temp_db: str, table: str) -> int:
    if table not in _ALLOWED_ACTION_TABLES:
        raise ValueError(f"unsupported table for test helper: {table!r}")
    conn = sqlite3.connect(temp_db)
    try:
        return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    finally:
        conn.close()


class TestSQLiteLikeRepositoryIntegration:
    """Integration tests for LikeRepository."""

    def test_write_and_read_likes_by_run_turn(
        self, seed_action_agents, temp_db, run_repo, like_repo
    ) -> None:
        """write_likes then read_likes_by_run_turn round-trips."""
        run_id = _make_run(run_repo)
        turn_number = 0
        _seed_turn_parent_row(temp_db, run_id, turn_number)

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
        self, seed_action_agents, temp_db, run_repo, comment_repo
    ) -> None:
        """write_comments then read_comments_by_run_turn round-trips."""
        run_id = _make_run(run_repo)
        turn_number = 0
        _seed_turn_parent_row(temp_db, run_id, turn_number)

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
        self, seed_action_agents, temp_db, run_repo, follow_repo
    ) -> None:
        """write_follows then read_follows_by_run_turn round-trips."""
        run_id = _make_run(run_repo)
        turn_number = 0
        _seed_turn_parent_row(temp_db, run_id, turn_number)

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


class TestSQLiteActionRepositoriesCanonicalOnly:
    """Negative paths: handle-shaped or malformed ids must not reach SQLite."""

    def test_write_likes_rejects_handle_agent_id_without_persisting(
        self, seed_action_agents, run_repo, like_repo, temp_db
    ) -> None:
        run_id = _make_run(run_repo)
        before = _count_rows(temp_db, "turn_likes")
        bad = GeneratedLikeFactory.create(
            like=LikeFactory.create(
                like_id="like_bad",
                agent_id="alice.bsky.social",
                post_id="at://did:plc:post1",
                created_at="2026-02-24T12:00:00Z",
            ),
            explanation="x",
            metadata=GenerationMetadataFactory.create(
                model_used=None,
                generation_metadata=None,
                created_at="2026-02-24T12:00:00Z",
            ),
        )
        with pytest.raises(ValueError, match="agent_id must be 16 lowercase hex chars"):
            like_repo.write_likes(run_id, 0, [bad])
        assert _count_rows(temp_db, "turn_likes") == before

    def test_write_comments_rejects_malformed_agent_id_without_persisting(
        self, seed_action_agents, run_repo, comment_repo, temp_db
    ) -> None:
        run_id = _make_run(run_repo)
        before = _count_rows(temp_db, "turn_comments")
        bad = GeneratedCommentFactory.create(
            comment=CommentFactory.create(
                comment_id="c_bad",
                agent_id="not-valid-hex",
                post_id="at://did:plc:post1",
                text="hi",
                created_at="2026-02-24T12:00:00Z",
            ),
            explanation="x",
            metadata=GenerationMetadataFactory.create(
                model_used=None,
                generation_metadata=None,
                created_at="2026-02-24T12:00:00Z",
            ),
        )
        with pytest.raises(ValueError, match="agent_id must be 16 lowercase hex chars"):
            comment_repo.write_comments(run_id, 0, [bad])
        assert _count_rows(temp_db, "turn_comments") == before

    def test_write_follows_rejects_handle_target_without_persisting(
        self, seed_action_agents, run_repo, follow_repo, temp_db
    ) -> None:
        run_id = _make_run(run_repo)
        before = _count_rows(temp_db, "turn_follows")
        alice_id = canonical_agent_id("alice.bsky.social")
        bad = GeneratedFollowFactory.create(
            follow=FollowFactory.create(
                follow_id="f_bad",
                agent_id=alice_id,
                target_agent_id="charlie.bsky.social",
                created_at="2026-02-24T12:00:00Z",
            ),
            explanation="x",
            metadata=GenerationMetadataFactory.create(
                model_used=None,
                generation_metadata=None,
                created_at="2026-02-24T12:00:00Z",
            ),
        )
        with pytest.raises(ValueError, match="agent_id must be 16 lowercase hex chars"):
            follow_repo.write_follows(run_id, 0, [bad])
        assert _count_rows(temp_db, "turn_follows") == before
