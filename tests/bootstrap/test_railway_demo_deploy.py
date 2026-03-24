from __future__ import annotations

import sqlite3

import pytest

from simulation.bootstrap.railway import (
    MARKER_FILENAME,
    marker_path_for_db,
    run_railway_demo_deploy_bootstrap,
)


class TestRailwayDemoDeployBootstrap:
    def test_marker_path_same_dir_as_db(self, tmp_path) -> None:
        db = tmp_path / "nested" / "db.sqlite"
        assert marker_path_for_db(db) == tmp_path / "nested" / MARKER_FILENAME

    def test_noop_when_flag_off(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        monkeypatch.delenv("LOCAL", raising=False)
        db = tmp_path / "db.sqlite"
        monkeypatch.setenv("SIM_DB_PATH", str(db))
        monkeypatch.delenv("RESET_DEMO_DB_ON_DEPLOY", raising=False)
        monkeypatch.setenv("RAILWAY_DEPLOYMENT_ID", "deploy-a")
        run_railway_demo_deploy_bootstrap()
        assert not db.exists()

    def test_noop_when_local_mode(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        monkeypatch.setenv("LOCAL", "true")
        db = tmp_path / "db.sqlite"
        monkeypatch.setenv("SIM_DB_PATH", str(db))
        monkeypatch.setenv("RESET_DEMO_DB_ON_DEPLOY", "1")
        monkeypatch.setenv("RAILWAY_DEPLOYMENT_ID", "deploy-a")
        run_railway_demo_deploy_bootstrap()
        assert not db.exists()

    def test_noop_when_deploy_id_missing(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        monkeypatch.delenv("LOCAL", raising=False)
        db = tmp_path / "db.sqlite"
        monkeypatch.setenv("SIM_DB_PATH", str(db))
        monkeypatch.setenv("RESET_DEMO_DB_ON_DEPLOY", "1")
        monkeypatch.delenv("RAILWAY_DEPLOYMENT_ID", raising=False)
        run_railway_demo_deploy_bootstrap()
        assert not db.exists()

    def test_new_deploy_then_same_skips_reset(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        monkeypatch.delenv("LOCAL", raising=False)
        db = tmp_path / "db.sqlite"
        monkeypatch.setenv("SIM_DB_PATH", str(db))
        monkeypatch.setenv("RESET_DEMO_DB_ON_DEPLOY", "1")
        monkeypatch.setenv("RAILWAY_DEPLOYMENT_ID", "deploy-1")

        run_railway_demo_deploy_bootstrap()
        assert db.is_file()
        m = marker_path_for_db(db)
        assert m.read_text(encoding="utf-8").strip() == "deploy-1"

        conn = sqlite3.connect(str(db))
        try:
            first_runs = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
        finally:
            conn.close()
        assert first_runs > 0

        run_railway_demo_deploy_bootstrap()
        conn = sqlite3.connect(str(db))
        try:
            second_runs = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
        finally:
            conn.close()
        assert second_runs == first_runs

    def test_new_deploy_id_resets_database(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        monkeypatch.delenv("LOCAL", raising=False)
        db = tmp_path / "db.sqlite"
        monkeypatch.setenv("SIM_DB_PATH", str(db))
        monkeypatch.setenv("RESET_DEMO_DB_ON_DEPLOY", "1")
        monkeypatch.setenv("RAILWAY_DEPLOYMENT_ID", "deploy-a")

        run_railway_demo_deploy_bootstrap()
        conn = sqlite3.connect(str(db))
        try:
            digest_a = conn.execute(
                "SELECT value FROM local_seed_meta WHERE key = 'fixtures_sha256'"
            ).fetchone()[0]
        finally:
            conn.close()

        monkeypatch.setenv("RAILWAY_DEPLOYMENT_ID", "deploy-b")
        run_railway_demo_deploy_bootstrap()

        conn = sqlite3.connect(str(db))
        try:
            digest_b = conn.execute(
                "SELECT value FROM local_seed_meta WHERE key = 'fixtures_sha256'"
            ).fetchone()[0]
        finally:
            conn.close()

        assert digest_a == digest_b
        assert digest_a  # seeded
        assert marker_path_for_db(db).read_text(encoding="utf-8").strip() == "deploy-b"
