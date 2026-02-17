"""Smoke tests for the simulation API against a running server.

Run only when SIMULATION_API_URL is set and a server is available:
    SIMULATION_API_URL=http://localhost:8000 uv run pytest -m smoke tests/api/test_simulation_smoke.py
Against a deployed URL:
    SIMULATION_API_URL=https://your-app.railway.app uv run pytest -m smoke tests/api/test_simulation_smoke.py
"""

import json
import os
import urllib.error
import urllib.request

import pytest

SIMULATION_API_URL_ENV: str = "SIMULATION_API_URL"


def _base_url() -> str:
    return os.environ.get(SIMULATION_API_URL_ENV, "").rstrip("/")


def _url(path: str) -> str:
    return f"{_base_url()}{path}"


@pytest.mark.smoke
@pytest.mark.skipif(
    not os.environ.get(SIMULATION_API_URL_ENV),
    reason=f"{SIMULATION_API_URL_ENV} not set; skip smoke tests unless running against live server",
)
def test_health_returns_200_and_ok():
    """GET /health returns 200 with status ok."""
    req = urllib.request.Request(_url("/health"), method="GET")
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
    expected_result = {"status": "ok"}
    assert data == expected_result


@pytest.mark.smoke
@pytest.mark.skipif(
    not os.environ.get(SIMULATION_API_URL_ENV),
    reason=f"{SIMULATION_API_URL_ENV} not set; skip smoke tests unless running against live server",
)
def test_post_simulations_run_returns_200_with_run_id_and_likes_per_turn():
    """POST /v1/simulations/run with minimal body returns 200 and expected fields."""
    payload = json.dumps({"num_agents": 1, "num_turns": 1}).encode()
    req = urllib.request.Request(
        _url("/v1/simulations/run"),
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
    expected_result = {
        "status": "completed",
        "error": None,
    }
    assert data["status"] == expected_result["status"]
    assert data["error"] is expected_result["error"]
    assert "run_id" in data and isinstance(data["run_id"], str)
    assert "likes_per_turn" in data and isinstance(data["likes_per_turn"], list)
    assert "total_likes" in data and isinstance(data["total_likes"], int)
