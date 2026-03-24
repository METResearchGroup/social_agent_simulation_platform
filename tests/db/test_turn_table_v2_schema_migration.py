"""Upgrade tests for the turn-table v2 schema spine (``f3c9a1e7b2d4``)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from lib.agent_id import canonical_agent_id
from lib.constants import REPO_ROOT


def _cfg(monkeypatch: pytest.MonkeyPatch, db_path: str) -> Config:
    monkeypatch.setenv("SIM_DB_PATH", db_path)
    monkeypatch.delenv("SIM_DATABASE_URL", raising=False)
    return Config(toml_file=str(Path(REPO_ROOT) / "pyproject.toml"))


def _fk_violations(conn: sqlite3.Connection) -> list:
    return conn.execute("PRAGMA foreign_key_check").fetchall()


class TestTurnTableV2SchemaMigration:
    def test_migrates_legacy_turn_rows_to_turn_family(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        db_path = str(tmp_path / "turn_v2.sqlite")
        cfg = _cfg(monkeypatch, db_path)
        command.upgrade(cfg, "e7f3a9c2d1b4")

        run_id = "run-turn-v2-test"
        handle_a = "alice.turnv2.bsky.social"
        handle_b = "bob.turnv2.bsky.social"
        agent_a = canonical_agent_id(handle_a)
        agent_b = canonical_agent_id(handle_b)

        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                """
                INSERT INTO runs (
                  run_id, app_user_id, created_at, total_turns, total_agents, feed_algorithm,
                  metric_keys, started_at, status, completed_at
                ) VALUES (?, NULL, '2026-01-01', 1, 2, 'chronological',
                  NULL, '2026-01-01', 'running', NULL)
                """,
                (run_id,),
            )
            for aid, h in ((agent_a, handle_a), (agent_b, handle_b)):
                conn.execute(
                    """
                    INSERT INTO agent (
                      agent_id, handle, persona_source, display_name, created_at, updated_at
                    ) VALUES (?, ?, 'test', 'Agent', '2026-01-01', '2026-01-01')
                    """,
                    (aid, h),
                )
            conn.execute(
                """
                INSERT INTO turn_metadata (
                  run_id, turn_number, total_actions, created_at
                ) VALUES (?, ?, ?, '2026-01-01')
                """,
                (
                    run_id,
                    0,
                    json.dumps({"like": 1, "comment": 1, "follow": 1}),
                ),
            )
            conn.execute(
                """
                INSERT INTO turn_metrics (run_id, turn_number, metrics, created_at)
                VALUES (?, ?, ?, '2026-01-01')
                """,
                (run_id, 0, json.dumps({"k": 1})),
            )
            conn.execute(
                """
                INSERT INTO generated_feeds (
                  feed_id, run_id, turn_number, agent_id, agent_handle, post_ids, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, '2026-01-01')
                """,
                ("feed-1", run_id, 0, agent_a, handle_a, json.dumps(["post-a"])),
            )
            conn.execute(
                """
                INSERT INTO likes (
                  like_id, run_id, turn_number, agent_id, post_id, created_at
                ) VALUES (?, ?, ?, ?, ?, '2026-01-01')
                """,
                ("like-1", run_id, 0, agent_a, "run-post-1"),
            )
            conn.execute(
                """
                INSERT INTO comments (
                  comment_id, run_id, turn_number, agent_id, post_id, text, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, '2026-01-01')
                """,
                ("comment-1", run_id, 0, agent_a, "run-post-1", "hi"),
            )
            conn.execute(
                """
                INSERT INTO follows (
                  follow_id, run_id, turn_number, agent_id, target_agent_id, created_at
                ) VALUES (?, ?, ?, ?, ?, '2026-01-01')
                """,
                ("follow-1", run_id, 0, agent_a, agent_b),
            )
            conn.commit()
        finally:
            conn.close()

        command.upgrade(cfg, "head")

        conn = sqlite3.connect(db_path)
        try:
            assert _fk_violations(conn) == []
            assert (
                conn.execute(
                    "SELECT COUNT(*) FROM turns WHERE run_id = ?", (run_id,)
                ).fetchone()[0]
                == 1
            )
            tm = conn.execute(
                "SELECT total_actions FROM turns WHERE run_id = ? AND turn_number = 0",
                (run_id,),
            ).fetchone()
            assert tm is not None
            assert json.loads(tm[0]) == {"like": 1, "comment": 1, "follow": 1}

            assert (
                conn.execute(
                    "SELECT COUNT(*) FROM turn_generated_feeds WHERE run_id = ?",
                    (run_id,),
                ).fetchone()[0]
                == 1
            )
            gf = conn.execute(
                "SELECT post_ids FROM turn_generated_feeds WHERE feed_id = ?",
                ("feed-1",),
            ).fetchone()
            assert gf is not None
            assert json.loads(gf[0]) == ["post-a"]

            assert (
                conn.execute(
                    "SELECT like_id FROM turn_likes WHERE run_id = ?", (run_id,)
                ).fetchone()[0]
                == "like-1"
            )
            assert (
                conn.execute(
                    "SELECT comment_id FROM turn_comments WHERE run_id = ?", (run_id,)
                ).fetchone()[0]
                == "comment-1"
            )
            assert (
                conn.execute(
                    "SELECT follow_id FROM turn_follows WHERE run_id = ?", (run_id,)
                ).fetchone()[0]
                == "follow-1"
            )
            assert conn.execute("SELECT COUNT(*) FROM turn_posts").fetchone()[0] == 0
        finally:
            conn.close()

    def test_fresh_head_database_exposes_turn_family_not_legacy_names(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        db_path = str(tmp_path / "turn_v2_fresh.sqlite")
        cfg = _cfg(monkeypatch, db_path)
        command.upgrade(cfg, "head")

        conn = sqlite3.connect(db_path)
        try:
            names = {
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                ).fetchall()
            }
            assert "turns" in names
            assert "turn_metrics" in names
            assert "turn_generated_feeds" in names
            assert "turn_likes" in names
            assert "turn_comments" in names
            assert "turn_follows" in names
            assert "turn_posts" in names
            assert "turn_metadata" not in names
            assert "generated_feeds" not in names
            assert "likes" not in names
            assert "comments" not in names
            assert "follows" not in names
        finally:
            conn.close()
