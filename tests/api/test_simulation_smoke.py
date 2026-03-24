"""Smoke tests for the simulation API against a running server.

Run only when SIMULATION_API_URL is set and a server is available:
    SIMULATION_API_URL=http://localhost:8000 uv run pytest -m smoke tests/api/test_simulation_smoke.py
Against a deployed URL (protected routes need a bearer token unless auth is bypassed):
    SIMULATION_API_URL=https://your-app.railway.app \\
      SIMULATION_API_BEARER_TOKEN=<token> uv run pytest -m smoke tests/api/test_simulation_smoke.py
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

import pytest

SIMULATION_API_URL_ENV: str = "SIMULATION_API_URL"
SIMULATION_API_BEARER_TOKEN_ENV: str = "SIMULATION_API_BEARER_TOKEN"


def _base_url() -> str:
    return os.environ.get(SIMULATION_API_URL_ENV, "").rstrip("/")


def _url(path: str) -> str:
    return f"{_base_url()}{path}"


def _optional_bearer_headers() -> dict[str, str]:
    token = os.environ.get(SIMULATION_API_BEARER_TOKEN_ENV, "").strip()
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def _merge_headers(base: dict[str, str] | None = None) -> dict[str, str]:
    out = dict(base or {})
    out.update(_optional_bearer_headers())
    return out


def _assert_run_response_contract(data: dict) -> None:
    """Assert POST /v1/simulations/run body matches current RunResponse shape."""
    required_top = (
        "run_id",
        "created_at",
        "status",
        "num_agents",
        "num_turns",
        "turns",
    )
    for key in required_top:
        assert key in data, f"RunResponse missing key {key!r}"
    assert isinstance(data["run_id"], str)
    assert isinstance(data["created_at"], str)
    assert data["status"] in ("completed", "failed")
    assert isinstance(data["num_agents"], int)
    assert isinstance(data["num_turns"], int)
    assert isinstance(data["turns"], list)

    if data["status"] == "completed":
        assert data.get("error") is None
    else:
        err = data.get("error")
        assert err is not None
        assert isinstance(err, dict)
        assert "code" in err
        assert "message" in err

    for turn in data["turns"]:
        assert isinstance(turn, dict)
        for tk in ("turn_number", "created_at", "total_actions", "metrics"):
            assert tk in turn, f"TurnSummaryItem missing {tk!r}"

    if data.get("run_metrics") is not None:
        assert isinstance(data["run_metrics"], dict)


def _get_json_expect_200(
    path: str,
    *,
    label: str,
    extra_headers: dict[str, str] | None = None,
) -> object:
    """GET JSON; fail with a clear message on 404 vs auth errors."""
    headers = _merge_headers(extra_headers)
    req = urllib.request.Request(_url(path), method="GET", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            assert resp.status == 200
            raw = resp.read().decode()
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        if e.code == 404:
            pytest.fail(
                f"{label}: route missing (HTTP 404) for {path}. "
                f"Backend/UI release skew may have dropped this endpoint. Body: {body[:500]}"
            )
        if e.code in (401, 403):
            pytest.fail(
                f"{label}: HTTP {e.code} for {path}. "
                f"Set {SIMULATION_API_BEARER_TOKEN_ENV} for deployed checks, or run the API "
                f"with DISABLE_AUTH=1 for local smoke. Body: {body[:500]}"
            )
        raise
    return json.loads(raw)


class TestSimulationSmoke:
    @pytest.mark.smoke
    @pytest.mark.skipif(
        not os.environ.get(SIMULATION_API_URL_ENV),
        reason=f"{SIMULATION_API_URL_ENV} not set; skip smoke tests unless running against live server",
    )
    def test_health_returns_200_and_ok(self):
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
    def test_post_simulations_run_returns_200_matching_run_response_contract(self):
        """POST /v1/simulations/run with minimal body returns 200 and RunResponse fields."""
        payload = json.dumps({"num_agents": 1, "num_turns": 1}).encode()
        headers = _merge_headers({"Content-Type": "application/json"})
        req = urllib.request.Request(
            _url("/v1/simulations/run"),
            data=payload,
            method="POST",
            headers=headers,
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                assert resp.status == 200
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            if e.code in (401, 403, 404):
                pytest.fail(
                    f"POST /v1/simulations/run: HTTP {e.code}. "
                    f"Set {SIMULATION_API_BEARER_TOKEN_ENV} for deployed checks, or run the API "
                    f"with DISABLE_AUTH=1 for local smoke. Body: {body[:500]}"
                )
            raise
        _assert_run_response_contract(data)

    @pytest.mark.smoke
    @pytest.mark.skipif(
        not os.environ.get(SIMULATION_API_URL_ENV),
        reason=f"{SIMULATION_API_URL_ENV} not set; skip smoke tests unless running against live server",
    )
    def test_get_simulations_metrics_returns_200_list(self):
        """GET /v1/simulations/metrics returns 200 and a list of metric metadata objects."""
        data = _get_json_expect_200(
            "/v1/simulations/metrics",
            label="metrics metadata",
        )
        assert isinstance(data, list)
        assert len(data) >= 1
        for item in data:
            assert isinstance(item, dict)
            for key in ("key", "display_name", "description", "scope", "author"):
                assert key in item, f"MetricSchema missing {key!r}"

    @pytest.mark.smoke
    @pytest.mark.skipif(
        not os.environ.get(SIMULATION_API_URL_ENV),
        reason=f"{SIMULATION_API_URL_ENV} not set; skip smoke tests unless running against live server",
    )
    def test_get_simulations_feed_algorithms_returns_200_list(self):
        """GET /v1/simulations/feed-algorithms returns 200 and algorithm metadata."""
        data = _get_json_expect_200(
            "/v1/simulations/feed-algorithms",
            label="feed algorithms",
        )
        assert isinstance(data, list)
        assert len(data) >= 1
        for item in data:
            assert isinstance(item, dict)
            for key in ("id", "display_name", "description"):
                assert key in item, f"FeedAlgorithmSchema missing {key!r}"
