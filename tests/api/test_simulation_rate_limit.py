"""Tests for rate limiting on POST /v1/simulations/run."""

from unittest.mock import MagicMock

from lib.timestamp_utils import get_current_timestamp
from simulation.core.models.actions import TurnAction
from simulation.core.models.metrics import RunMetrics, TurnMetrics
from simulation.core.models.runs import Run, RunStatus
from simulation.core.models.turns import TurnMetadata


def _make_mock_engine():
    """Create a mock engine that returns a successful run."""
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


def test_post_simulations_run_rate_limit_returns_429_after_limit_exceeded(
    simulation_client,
):
    """Sixth request within limit window returns 429 with RATE_LIMITED error shape.

    Uses a unique X-Forwarded-For IP to get a fresh rate limit slot, independent
    of other tests.
    """
    client, fastapi_app = simulation_client
    fastapi_app.state.engine = _make_mock_engine()

    headers = {
        "Content-Type": "application/json",
        "X-Forwarded-For": "192.168.100.1",
    }
    payload = {"num_agents": 1, "num_turns": 1}

    responses = []
    for _ in range(6):
        resp = client.post("/v1/simulations/run", json=payload, headers=headers)
        responses.append(resp)

    assert all(r.status_code == 200 for r in responses[:5]), (
        "First 5 requests should succeed"
    )
    assert responses[5].status_code == 429, "Sixth request should be rate limited"

    data = responses[5].json()
    assert data["error"]["code"] == "RATE_LIMITED"
    assert data["error"]["message"] == "Rate limit exceeded"
    assert data["error"]["detail"] is None


def test_post_simulations_run_rate_limit_429_error_shape(simulation_client):
    """429 response has standard error structure matching other API errors."""
    client, fastapi_app = simulation_client
    fastapi_app.state.engine = _make_mock_engine()

    headers = {
        "Content-Type": "application/json",
        "X-Forwarded-For": "192.168.100.2",
    }
    payload = {"num_agents": 1, "num_turns": 1}

    for _ in range(6):
        response = client.post("/v1/simulations/run", json=payload, headers=headers)

    assert response.status_code == 429
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "RATE_LIMITED"
    assert data["error"]["message"] == "Rate limit exceeded"
    assert "detail" in data["error"]
