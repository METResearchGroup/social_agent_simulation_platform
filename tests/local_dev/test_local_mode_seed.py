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


def test_get_db_path__local_forces_dummy_db_and_logs_override(
    monkeypatch, caplog
) -> None:
    monkeypatch.setenv("LOCAL", "true")
    monkeypatch.setenv(SIM_DB_PATH_ENV, "/tmp/some_other.sqlite")

    caplog.clear()
    caplog.set_level("WARNING")
    path = get_db_path()

    expected_result = LOCAL_DEV_DB_PATH
    assert path == expected_result
    expected_result = True
    assert (
        any("LOCAL=true overrides" in r.message for r in caplog.records)
        is expected_result
    )


def test_seed_local_db_if_needed__idempotent(temp_db, caplog) -> None:
    caplog.clear()
    caplog.set_level("INFO")

    seed_local_db_if_needed(db_path=temp_db, fixtures_dir=FIXTURES_DIR)

    conn = sqlite3.connect(temp_db)
    try:
        row = conn.execute(
            "SELECT value FROM local_seed_meta WHERE key = 'fixtures_sha256'"
        ).fetchone()
        expected_result = True
        assert (row is not None) is expected_result
        expected_result = _fixtures_digest(FIXTURES_DIR)
        assert row[0] == expected_result

        runs_count = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
        expected_result = True
        assert (runs_count > 0) is expected_result
    finally:
        conn.close()

    # Second call should be a no-op (same digest).
    seed_local_db_if_needed(db_path=temp_db, fixtures_dir=FIXTURES_DIR)
    expected_result = True
    assert (
        any("Local seed already applied" in r.message for r in caplog.records)
        is expected_result
    )


def test_api_endpoints__db_backed_with_seeded_db(temp_db, monkeypatch) -> None:
    # Seed the temp DB used by the engine.
    seed_local_db_if_needed(db_path=temp_db, fixtures_dir=FIXTURES_DIR)

    # Bypass auth for API calls in tests.
    monkeypatch.setenv("DISABLE_AUTH", "1")

    with TestClient(app) as client:
        runs = client.get("/v1/simulations/runs").json()
        expected_result = True
        assert isinstance(runs, list) is expected_result
        expected_result = True
        assert (len(runs) > 0) is expected_result

        run_id = runs[0]["run_id"]
        run_details = client.get(f"/v1/simulations/runs/{run_id}").json()
        expected_result = run_id
        assert run_details["run_id"] == expected_result
        expected_result = True
        assert (run_details.get("run_metrics") is not None) is expected_result

        turns_by_id = client.get(f"/v1/simulations/runs/{run_id}/turns").json()
        expected_result = True
        assert isinstance(turns_by_id, dict) is expected_result

        # Extract some post IDs (if present) and ensure /posts hydrates them.
        some_post_ids: list[str] = []
        for turn in turns_by_id.values():
            agent_feeds = turn.get("agent_feeds", {})
            for feed in agent_feeds.values():
                some_post_ids.extend(feed.get("post_ids", []))
            if some_post_ids:
                break
        expected_result = True
        assert bool(some_post_ids) is expected_result, (
            "Seeded turns should include post IDs"
        )

        url = "/v1/simulations/posts?" + "&".join(
            f"post_ids={pid}" for pid in some_post_ids[:3]
        )
        posts = client.get(url).json()
        expected_result = True
        assert isinstance(posts, list) is expected_result
        expected_result = True
        assert (len(posts) > 0) is expected_result
