from __future__ import annotations

import sqlite3

from fastapi.testclient import TestClient

from db.adapters.sqlite.sqlite import LOCAL_DEV_DB_PATH, SIM_DB_PATH_ENV, get_db_path
from simulation.api.main import app
from simulation.local_dev.seed_loader import (
    FIXTURES_DIR,
    _fixtures_digest,
    seed_local_db_if_needed,
)


class TestLocalModeSeed:
    def test_get_db_path__local_forces_dummy_db_and_logs_override(
        self, monkeypatch, caplog
    ) -> None:
        monkeypatch.setenv("LOCAL", "true")
        monkeypatch.setenv(SIM_DB_PATH_ENV, "/tmp/some_other.sqlite")

        caplog.clear()
        caplog.set_level("WARNING")
        path = get_db_path()

        assert path == LOCAL_DEV_DB_PATH
        assert any("LOCAL=true overrides" in r.message for r in caplog.records)

    def test_seed_local_db_if_needed__idempotent(self, temp_db, caplog) -> None:
        caplog.clear()
        caplog.set_level("INFO")

        seed_local_db_if_needed(db_path=temp_db, fixtures_dir=FIXTURES_DIR)

        conn = sqlite3.connect(temp_db)
        try:
            row = conn.execute(
                "SELECT value FROM local_seed_meta WHERE key = 'fixtures_sha256'"
            ).fetchone()
            assert row is not None
            assert row[0] == _fixtures_digest(FIXTURES_DIR)

            runs_count = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
            assert runs_count > 0
            follow_edges_count = conn.execute(
                "SELECT COUNT(*) FROM agent_follow_edges"
            ).fetchone()[0]
            assert follow_edges_count > 0
        finally:
            conn.close()

        # Second call should be a no-op (same digest).
        conn = sqlite3.connect(temp_db)
        try:
            fixtures_sha256_before = conn.execute(
                "SELECT value FROM local_seed_meta WHERE key = 'fixtures_sha256'"
            ).fetchone()[0]
            runs_count_before = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
        finally:
            conn.close()

        seed_local_db_if_needed(db_path=temp_db, fixtures_dir=FIXTURES_DIR)

        conn = sqlite3.connect(temp_db)
        try:
            fixtures_sha256_after = conn.execute(
                "SELECT value FROM local_seed_meta WHERE key = 'fixtures_sha256'"
            ).fetchone()[0]
            runs_count_after = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
        finally:
            conn.close()

        expected_digest = _fixtures_digest(FIXTURES_DIR)
        assert fixtures_sha256_before == expected_digest
        assert fixtures_sha256_after == expected_digest
        assert fixtures_sha256_after == fixtures_sha256_before
        assert runs_count_after == runs_count_before

        assert any("Local seed already applied" in r.message for r in caplog.records)

    def test_seed_local_db_if_needed__syncs_follow_edge_metadata(
        self,
        temp_db,
    ) -> None:
        seed_local_db_if_needed(db_path=temp_db, fixtures_dir=FIXTURES_DIR)

        conn = sqlite3.connect(temp_db)
        try:
            alice_counts = conn.execute(
                """
                SELECT followers_count, follows_count
                FROM user_agent_profile_metadata
                WHERE agent_id = 'agent_0240dc0d4a4c7e73'
                """
            ).fetchone()
            edward_counts = conn.execute(
                """
                SELECT followers_count, follows_count
                FROM user_agent_profile_metadata
                WHERE agent_id = 'agent_d5aaff22974ebc2c'
                """
            ).fetchone()
        finally:
            conn.close()

        assert alice_counts == (5, 2)
        assert edward_counts == (0, 1)

    def test_api_endpoints__db_backed_with_seeded_db(
        self, temp_db, monkeypatch
    ) -> None:
        # Seed the temp DB used by the engine.
        seed_local_db_if_needed(db_path=temp_db, fixtures_dir=FIXTURES_DIR)

        # Bypass auth for API calls in tests.
        monkeypatch.setenv("DISABLE_AUTH", "1")

        with TestClient(app) as client:
            runs = client.get("/v1/simulations/runs").json()
            assert isinstance(runs, list)
            assert len(runs) > 0

            run_id = runs[0]["run_id"]
            run_details = client.get(f"/v1/simulations/runs/{run_id}").json()
            assert run_details["run_id"] == run_id
            assert run_details.get("run_metrics") is not None

            turns_by_id = client.get(f"/v1/simulations/runs/{run_id}/turns").json()
            assert isinstance(turns_by_id, dict)

            # Extract some post IDs (if present) and ensure /posts hydrates them.
            some_post_ids: list[str] = []
            for turn in turns_by_id.values():
                agent_feeds = turn.get("agent_feeds", {})
                for feed in agent_feeds.values():
                    some_post_ids.extend(feed.get("post_ids", []))
                if some_post_ids:
                    break
            assert some_post_ids, "Seeded turns should include post IDs"

            url = "/v1/simulations/posts?" + "&".join(
                f"post_ids={pid}" for pid in some_post_ids[:3]
            )
            posts = client.get(url).json()
            assert isinstance(posts, list)
            assert len(posts) > 0
