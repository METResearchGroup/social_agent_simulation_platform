"""Tests for rate limiting on POST /v1/simulations/run."""

from unittest.mock import MagicMock

import pytest

from lib.timestamp_utils import get_current_timestamp
from simulation.core.models.actions import TurnAction
from simulation.core.models.metrics import RunMetrics, TurnMetrics
from simulation.core.models.runs import Run, RunStatus
from simulation.core.models.turns import TurnMetadata


@pytest.fixture
def mock_engine_minimal_success():
    """Mock engine that returns a minimal successful 1-turn run. Reused across rate limit tests."""
    run = Run(
        run_id="run-rate-limit-test",
        created_at=get_current_timestamp(),
        total_turns=1,
        total_agents=1,
        feed_algorithm="chronological",
        started_at=get_current_timestamp(),
        status=RunStatus.COMPLETED,
        completed_at=get_current_timestamp(),
    )
    metadata_list = [
        TurnMetadata(
            run_id=run.run_id,
            turn_number=0,
            total_actions={
                TurnAction.LIKE: 0,
                TurnAction.COMMENT: 0,
                TurnAction.FOLLOW: 0,
            },
            created_at=run.created_at,
        ),
    ]
    turn_metrics_list = [
        TurnMetrics(
            run_id=run.run_id,
            turn_number=0,
            metrics={"turn.actions.total": 0},
            created_at=run.created_at,
        )
    ]
    run_metrics = RunMetrics(
        run_id=run.run_id,
        metrics={"run.actions.total": 0},
        created_at=run.created_at,
    )
    mock = MagicMock()
    mock.execute_run.return_value = run
    mock.list_turn_metadata.return_value = metadata_list
    mock.list_turn_metrics.return_value = turn_metrics_list
    mock.get_run_metrics.return_value = run_metrics
    return mock


def _trigger_rate_limit(client, fastapi_app, ip: str, mock_engine) -> list:
    """Exceed rate limit by making 6 requests. Returns list of 6 responses."""
    fastapi_app.state.limiter.reset()
    fastapi_app.state.engine = mock_engine
    headers = {"Content-Type": "application/json", "X-Forwarded-For": ip}
    payload = {"num_agents": 1, "num_turns": 1}
    return [
        client.post("/v1/simulations/run", json=payload, headers=headers)
        for _ in range(6)
    ]


def test_post_simulations_run_rate_limit_returns_429_after_limit_exceeded(
    simulation_client,
    mock_engine_minimal_success,
):
    """Sixth request within limit window returns 429 with RATE_LIMITED error shape.

    Resets the shared limiter storage so the six-request sequence is deterministic
    regardless of test order.
    """
    client, fastapi_app = simulation_client
    responses = _trigger_rate_limit(
        client, fastapi_app, "192.168.100.1", mock_engine_minimal_success
    )

    assert all(r.status_code == 200 for r in responses[:5]), (
        "First 5 requests should succeed"
    )
    assert responses[5].status_code == 429, "Sixth request should be rate limited"

    data = responses[5].json()
    assert data["error"]["code"] == "RATE_LIMITED"
    assert data["error"]["message"] == "Rate limit exceeded"
    assert data["error"]["detail"] is None


def test_post_simulations_run_rate_limit_429_error_shape(
    simulation_client,
    mock_engine_minimal_success,
):
    """429 response has standard error structure matching other API errors."""
    client, fastapi_app = simulation_client
    responses = _trigger_rate_limit(
        client, fastapi_app, "192.168.100.2", mock_engine_minimal_success
    )
    response = responses[5]

    assert response.status_code == 429
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "RATE_LIMITED"
    assert data["error"]["message"] == "Rate limit exceeded"
    assert "detail" in data["error"]
