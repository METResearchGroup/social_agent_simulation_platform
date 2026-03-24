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
import urllib.parse
import urllib.request
from datetime import datetime

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


def _path_segment(value: str) -> str:
    """Encode a single path segment (e.g. agent handle with @)."""
    return urllib.parse.quote(value, safe="")


def _assert_iso8601_timestamp(value: object, *, label: str) -> None:
    """API timestamps must parse like ``new Date(s)`` in the browser (avoids UI \"Invalid Date\")."""
    assert isinstance(value, str), f"{label}: expected str, got {type(value).__name__}"
    text = value.strip()
    assert text, f"{label}: empty timestamp"
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        datetime.fromisoformat(text)
    except ValueError as e:
        raise AssertionError(
            f"{label}: not ISO-8601 parseable (UI shows Invalid Date): {value!r}"
        ) from e


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

            # Registry / form defaults (lists or non-empty config fields).
            metrics = _get_json(f"{base_url}/v1/simulations/metrics")
            assert isinstance(metrics, list)
            assert len(metrics) >= 1

            feeds = _get_json(f"{base_url}/v1/simulations/feed-algorithms")
            assert isinstance(feeds, list)
            assert len(feeds) >= 1

            default_cfg = _get_json(f"{base_url}/v1/simulations/config/default")
            assert isinstance(default_cfg, dict)
            assert int(default_cfg["num_agents"]) >= 1
            assert int(default_cfg["num_turns"]) >= 1
            assert isinstance(default_cfg["metric_keys"], list)
            assert len(default_cfg["metric_keys"]) >= 1

            # View agents: non-empty list and fields the UI maps (see ui/lib/api/simulation.ts mapAgent).
            agents = _get_json(f"{base_url}/v1/simulations/agents")
            assert isinstance(agents, list)
            assert len(agents) >= 1
            for i, agent in enumerate(agents):
                assert isinstance(agent, dict)
                assert str(agent.get("handle", "")).strip(), (
                    f"agents[{i}].handle missing (View agents would show empty)"
                )
                for key in ("name", "bio", "generated_bio"):
                    assert key in agent, f"agents[{i}] missing {key!r}"
                for key in ("followers", "following", "posts_count"):
                    assert isinstance(agent.get(key), int), (
                        f"agents[{i}].{key} must be int for UI counts"
                    )
                    assert int(agent[key]) >= 0

            follows_nonzero = False
            for agent in agents:
                handle = str(agent["handle"])
                follows = _get_json(
                    f"{base_url}/v1/simulations/agents/{_path_segment(handle)}/follows"
                )
                assert isinstance(follows, dict)
                assert "total" in follows
                assert "items" in follows
                total = int(follows["total"])
                items = follows["items"]
                assert isinstance(items, list)
                if total >= 1 and len(items) >= 1:
                    follows_nonzero = True
                    break
            assert follows_nonzero, (
                "expected at least one agent with seed follow edges (check fixtures)"
            )

            # Global post catalog from seeded feed_posts.
            posts = _get_json(f"{base_url}/v1/simulations/posts")
            assert isinstance(posts, list)
            assert len(posts) >= 1

            runs = _get_json(f"{base_url}/v1/simulations/runs")
            assert isinstance(runs, list)
            assert len(runs) >= 1

            # Run list: created_at must parse in the browser (prod showed \"Invalid Date\" otherwise).
            for i, run in enumerate(runs):
                assert isinstance(run, dict)
                _assert_iso8601_timestamp(
                    run.get("created_at"), label=f"runs[{i}].created_at"
                )
                assert run.get("status") in ("completed", "running", "failed")
                assert int(run.get("total_turns", -1)) >= 0

            completed = next(
                (r for r in runs if r.get("status") == "completed"),
                None,
            )
            assert completed is not None, (
                "seed must include at least one completed run for turn/UI parity checks"
            )
            run_id = str(completed["run_id"])
            assert int(completed["total_turns"]) >= 1

            detail = _get_json(
                f"{base_url}/v1/simulations/runs/{_path_segment(run_id)}"
            )
            assert isinstance(detail, dict)
            assert detail.get("run_id") == run_id
            assert detail.get("status") == "completed"
            _assert_iso8601_timestamp(
                detail.get("created_at"), label="detail.created_at"
            )
            _assert_iso8601_timestamp(
                detail.get("started_at"), label="detail.started_at"
            )
            if detail.get("completed_at") is not None:
                _assert_iso8601_timestamp(
                    detail["completed_at"], label="detail.completed_at"
                )

            turn_rows = detail.get("turns")
            assert isinstance(turn_rows, list)
            assert len(turn_rows) >= 1
            assert len(turn_rows) == int(completed["total_turns"]), (
                "run summary total_turns should match detail.turns length for completed seed run"
            )
            for j, row in enumerate(turn_rows):
                assert isinstance(row, dict)
                _assert_iso8601_timestamp(
                    row.get("created_at"), label=f"detail.turns[{j}].created_at"
                )

            turns = _get_json(
                f"{base_url}/v1/simulations/runs/{_path_segment(run_id)}/turns"
            )
            assert isinstance(turns, dict)
            assert len(turns) >= 1
            assert len(turns) == int(completed["total_turns"]), (
                "GET .../turns key count should match completed total_turns"
            )
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=10)
