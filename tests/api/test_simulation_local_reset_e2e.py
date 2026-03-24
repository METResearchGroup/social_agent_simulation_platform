"""End-to-end tests: disposable SQLite, migrate, seed, subprocess uvicorn, HTTP checks.

Runs locally or in the dedicated ``ci-e2e`` GitHub Actions workflow (``RUN_LOCAL_RESET_E2E=1``).
Skipped in the default CI ``test`` matrix so the Python matrix stays fast.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

import pytest

from db.adapters.sqlite.sqlite import initialize_database
from lib.constants import REPO_ROOT
from simulation.bootstrap.railway import _delete_sqlite_cluster
from simulation.local_dev.seed_loader import seed_database_from_fixtures_if_needed


def _pick_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _wait_for_health(base_url: str, *, timeout_s: float = 60.0) -> None:
    deadline = time.monotonic() + timeout_s
    last_err: Exception | None = None
    while time.monotonic() < deadline:
        try:
            req = urllib.request.Request(f"{base_url}/health", method="GET")
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    body = json.loads(resp.read().decode())
                    if body == {"status": "ok"}:
                        return
        except (
            urllib.error.URLError,
            TimeoutError,
            OSError,
            json.JSONDecodeError,
        ) as e:
            last_err = e
        time.sleep(0.25)
    msg = f"Server did not become healthy at {base_url}/health within {timeout_s}s"
    if last_err is not None:
        raise AssertionError(msg) from last_err
    raise AssertionError(msg)


def _get_json(url: str) -> object:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        assert resp.status == 200
        return json.loads(resp.read().decode())


@pytest.mark.e2e
@pytest.mark.skipif(
    os.environ.get("GITHUB_ACTIONS") == "true"
    and os.environ.get("RUN_LOCAL_RESET_E2E") != "1",
    reason=(
        "Local reset E2E runs in the dedicated CI workflow or locally; "
        "skipped in the default CI pytest matrix."
    ),
)
class TestLocalResetE2E:
    def test_fresh_db_migrate_seed_and_http_contract(
        self, monkeypatch, tmp_path
    ) -> None:
        db_path = tmp_path / "e2e.sqlite"
        monkeypatch.delenv("LOCAL", raising=False)
        monkeypatch.delenv("SIM_DATABASE_URL", raising=False)
        monkeypatch.setenv("SIM_DB_PATH", str(db_path))

        _delete_sqlite_cluster(db_path)
        initialize_database()
        seed_database_from_fixtures_if_needed(db_path=str(db_path))

        port = _pick_loopback_port()
        base_url = f"http://127.0.0.1:{port}"

        env = os.environ.copy()
        env.pop("LOCAL", None)
        env.pop("SIM_DATABASE_URL", None)
        env["SIM_DB_PATH"] = str(db_path)
        env["DISABLE_AUTH"] = "1"
        env["PYTHONPATH"] = REPO_ROOT

        proc = subprocess.Popen(  # noqa: S603
            [
                sys.executable,
                "-m",
                "uvicorn",
                "simulation.api.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            env=env,
            cwd=REPO_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            _wait_for_health(base_url)

            metrics = _get_json(f"{base_url}/v1/simulations/metrics")
            assert isinstance(metrics, list)
            assert len(metrics) >= 1

            feeds = _get_json(f"{base_url}/v1/simulations/feed-algorithms")
            assert isinstance(feeds, list)
            assert len(feeds) >= 1

            runs = _get_json(f"{base_url}/v1/simulations/runs")
            assert isinstance(runs, list)
            assert len(runs) >= 1
            run_id = runs[0]["run_id"]
            assert isinstance(run_id, str)

            detail = _get_json(f"{base_url}/v1/simulations/runs/{run_id}")
            assert isinstance(detail, dict)
            assert detail.get("run_id") == run_id

            turns = _get_json(f"{base_url}/v1/simulations/runs/{run_id}/turns")
            assert isinstance(turns, dict)
            assert len(turns) >= 1
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=10)
