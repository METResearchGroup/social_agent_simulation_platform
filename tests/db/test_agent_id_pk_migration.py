"""Upgrade tests for the canonical agent_id data migration (``c3d5e7f9a0b2``)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from lib.agent_id import canonical_agent_id, is_canonical_agent_id
from lib.constants import REPO_ROOT
from scripts.migrations.agent_id_migration import (
    AgentIdMigrationCollisionError,
    stable_source_for_agent_row,
)


def _cfg(monkeypatch: pytest.MonkeyPatch, db_path: str) -> Config:
    monkeypatch.setenv("SIM_DB_PATH", db_path)
    monkeypatch.delenv("SIM_DATABASE_URL", raising=False)
    return Config(toml_file=str(Path(REPO_ROOT) / "pyproject.toml"))


def _fk_violations(conn: sqlite3.Connection) -> list:
    return conn.execute("PRAGMA foreign_key_check").fetchall()


class TestAgentIdPkMigration:
    def test_rewrites_agent_and_agent_posts(self, tmp_path: Path, monkeypatch) -> None:
        db_path = str(tmp_path / "m1.sqlite")
        cfg = _cfg(monkeypatch, db_path)
        command.upgrade(cfg, "b2c4d6e8f0a1")

        legacy = "550e8400-e29b-41d4-a716-446655440000"
        handle = "alice.integration.bsky.social"
        expected = canonical_agent_id(handle)

        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                """
                INSERT INTO agent (
                  agent_id, handle, persona_source, display_name, created_at, updated_at
                ) VALUES (?, ?, 'test', 'Alice', '2026-01-01', '2026-01-01')
                """,
                (legacy, handle),
            )
            conn.execute(
                """
                INSERT INTO agent_posts (
                  agent_post_id, agent_id, body_text, published_at, created_at, updated_at
                ) VALUES (?, ?, 'body', '2026-01-01', '2026-01-01', '2026-01-01')
                """,
                ("post-1", legacy),
            )
            conn.commit()
        finally:
            conn.close()

        command.upgrade(cfg, "head")

        conn = sqlite3.connect(db_path)
        try:
            assert _fk_violations(conn) == []
            row = conn.execute(
                "SELECT agent_id FROM agent WHERE handle = ?", (handle,)
            ).fetchone()
            assert row is not None
            assert row[0] == expected
            assert is_canonical_agent_id(row[0])
            post = conn.execute(
                "SELECT agent_id FROM agent_posts WHERE agent_post_id = ?", ("post-1",)
            ).fetchone()
            assert post is not None
            assert post[0] == expected
        finally:
            conn.close()

    def test_uses_bluesky_did_when_joined(self, tmp_path: Path, monkeypatch) -> None:
        db_path = str(tmp_path / "m2.sqlite")
        cfg = _cfg(monkeypatch, db_path)
        command.upgrade(cfg, "b2c4d6e8f0a1")

        legacy = "660e8400-e29b-41d4-a716-446655440001"
        handle = "bob.integration.bsky.social"
        did = "did:plc:integrationbob"
        expected = canonical_agent_id(did)
        assert (
            stable_source_for_agent_row(
                handle=handle, legacy_agent_id=legacy, bluesky_did=did
            )
            == did
        )

        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                """
                INSERT INTO bluesky_profiles (
                  handle, did, display_name, bio, followers_count, follows_count, posts_count
                ) VALUES (?, ?, 'Bob', '', 0, 0, 0)
                """,
                (handle, did),
            )
            conn.execute(
                """
                INSERT INTO agent (
                  agent_id, handle, persona_source, display_name, created_at, updated_at
                ) VALUES (?, ?, 'test', 'Bob', '2026-01-01', '2026-01-01')
                """,
                (legacy, handle),
            )
            conn.commit()
        finally:
            conn.close()

        command.upgrade(cfg, "head")

        conn = sqlite3.connect(db_path)
        try:
            assert _fk_violations(conn) == []
            row = conn.execute(
                "SELECT agent_id FROM agent WHERE handle = ?", (handle,)
            ).fetchone()
            assert row is not None
            assert row[0] == expected
        finally:
            conn.close()

    def test_rewrites_run_agents_composite_refs(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        db_path = str(tmp_path / "m3.sqlite")
        cfg = _cfg(monkeypatch, db_path)
        command.upgrade(cfg, "b2c4d6e8f0a1")

        legacy = "770e8400-e29b-41d4-a716-446655440002"
        handle = "carol.integration.bsky.social"
        expected = canonical_agent_id(handle)
        run_id = "run-migration-test"
        run_post_id = "rp-1"

        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                """
                INSERT INTO runs (
                  run_id, app_user_id, created_at, total_turns, total_agents, feed_algorithm,
                  metric_keys, started_at, status, completed_at
                ) VALUES (?, NULL, '2026-01-01', 1, 1, 'chronological',
                  NULL, '2026-01-01', 'completed', '2026-01-01')
                """,
                (run_id,),
            )
            conn.execute(
                """
                INSERT INTO agent (
                  agent_id, handle, persona_source, display_name, created_at, updated_at
                ) VALUES (?, ?, 'test', 'Carol', '2026-01-01', '2026-01-01')
                """,
                (legacy, handle),
            )
            conn.execute(
                """
                INSERT INTO run_agents (
                  run_id, agent_id, selection_order, handle_at_start, display_name_at_start,
                  persona_bio_at_start, followers_count_at_start, follows_count_at_start,
                  posts_count_at_start, created_at
                ) VALUES (?, ?, 1, ?, 'Carol', '', 0, 0, 0, '2026-01-01')
                """,
                (run_id, legacy, handle),
            )
            conn.execute(
                """
                INSERT INTO agent_posts (
                  agent_post_id, agent_id, body_text, published_at, created_at, updated_at
                ) VALUES (?, ?, 'x', '2026-01-01', '2026-01-01', '2026-01-01')
                """,
                ("agent-post-1", legacy),
            )
            conn.execute(
                """
                INSERT INTO run_posts (
                  run_post_id, run_id, agent_post_id, author_agent_id,
                  author_handle_at_start, author_display_name_at_start, body_text_at_start,
                  published_at_start, source_post_id_at_start, source_at_start, source_uri_at_start,
                  created_at
                ) VALUES (?, ?, ?, ?, ?, ?, '', '2026-01-01', NULL, NULL, NULL, '2026-01-01')
                """,
                (run_post_id, run_id, "agent-post-1", legacy, handle, "Carol"),
            )
            conn.commit()
        finally:
            conn.close()

        command.upgrade(cfg, "head")

        conn = sqlite3.connect(db_path)
        try:
            assert _fk_violations(conn) == []
            ra = conn.execute(
                "SELECT agent_id FROM run_agents WHERE run_id = ? AND handle_at_start = ?",
                (run_id, handle),
            ).fetchone()
            assert ra is not None
            assert ra[0] == expected
            rp = conn.execute(
                "SELECT author_agent_id FROM run_posts WHERE run_post_id = ?",
                (run_post_id,),
            ).fetchone()
            assert rp is not None
            assert rp[0] == expected
        finally:
            conn.close()

    def test_aborts_on_collision(self, tmp_path: Path, monkeypatch) -> None:
        db_path = str(tmp_path / "m4.sqlite")
        cfg = _cfg(monkeypatch, db_path)
        command.upgrade(cfg, "b2c4d6e8f0a1")

        shared_did = "did:plc:collides"
        conn = sqlite3.connect(db_path)
        try:
            for idx, (legacy, h) in enumerate(
                [
                    (
                        "880e8400-e29b-41d4-a716-446655440003",
                        "d1.integration.bsky.social",
                    ),
                    (
                        "990e8400-e29b-41d4-a716-446655440004",
                        "d2.integration.bsky.social",
                    ),
                ]
            ):
                conn.execute(
                    """
                    INSERT INTO bluesky_profiles (
                      handle, did, display_name, bio, followers_count, follows_count, posts_count
                    ) VALUES (?, ?, 'x', '', 0, 0, 0)
                    """,
                    (h, shared_did),
                )
                conn.execute(
                    """
                    INSERT INTO agent (
                      agent_id, handle, persona_source, display_name, created_at, updated_at
                    ) VALUES (?, ?, 'test', ?, '2026-01-01', '2026-01-01')
                    """,
                    (legacy, h, f"A{idx}"),
                )
            conn.commit()
        finally:
            conn.close()

        with pytest.raises(AgentIdMigrationCollisionError):
            command.upgrade(cfg, "head")
