"""Tests for metric_keys in run request and run details."""

from unittest.mock import MagicMock

from lib.timestamp_utils import get_current_timestamp
from simulation.core.metrics.defaults import (
    DEFAULT_RUN_METRIC_KEYS,
    DEFAULT_TURN_METRIC_KEYS,
)
from simulation.core.models.actions import TurnAction
from simulation.core.models.metrics import RunMetrics, TurnMetrics
from simulation.core.models.runs import Run, RunStatus
from simulation.core.models.turns import TurnMetadata


def _make_mock_engine_with_metric_keys(
    run_metric_keys: list[str] | None = None,
) -> MagicMock:
    """Create mock engine returning run with given metric_keys."""
    keys = run_metric_keys or sorted(
        set(DEFAULT_TURN_METRIC_KEYS + DEFAULT_RUN_METRIC_KEYS)
    )
    run = Run(
        run_id="run-metrics-test",
        created_at=get_current_timestamp(),
        total_turns=1,
        total_agents=1,
        feed_algorithm="chronological",
        metric_keys=keys,
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
    mock.get_run.return_value = run
    return mock


def test_post_run_with_metric_keys_returns_details_with_keys(simulation_client):
    """POST with metric_keys returns run; GET details includes those keys in config."""
    client, fastapi_app = simulation_client
    custom_keys = [
        "turn.actions.counts_by_type",
        "turn.actions.total",
        "run.actions.total",
    ]
    fastapi_app.state.engine = _make_mock_engine_with_metric_keys(
        run_metric_keys=custom_keys
    )
    create_resp = client.post(
        "/v1/simulations/run",
        json={
            "num_agents": 1,
            "num_turns": 1,
            "metric_keys": custom_keys,
        },
    )
    assert create_resp.status_code == 200
    run_id = create_resp.json()["run_id"]

    details_resp = client.get(
        f"/v1/simulations/runs/{run_id}",
    )
    assert details_resp.status_code == 200
    config = details_resp.json()["config"]
    assert "metric_keys" in config
    assert sorted(config["metric_keys"]) == sorted(custom_keys)


def test_post_run_without_metric_keys_uses_defaults(simulation_client):
    """POST without metric_keys uses default built-in keys."""
    client, fastapi_app = simulation_client
    default_keys = sorted(set(DEFAULT_TURN_METRIC_KEYS + DEFAULT_RUN_METRIC_KEYS))
    fastapi_app.state.engine = _make_mock_engine_with_metric_keys(
        run_metric_keys=default_keys
    )
    create_resp = client.post(
        "/v1/simulations/run",
        json={"num_agents": 1, "num_turns": 1},
    )
    assert create_resp.status_code == 200

    run_id = create_resp.json()["run_id"]
    details_resp = client.get(
        f"/v1/simulations/runs/{run_id}",
    )
    assert details_resp.status_code == 200
    config = details_resp.json()["config"]
    assert sorted(config["metric_keys"]) == default_keys


def test_post_run_with_invalid_metric_key_returns_422(simulation_client):
    """POST with unknown metric key returns 422 validation error."""
    client, fastapi_app = simulation_client
    fastapi_app.state.engine = _make_mock_engine_with_metric_keys()
    create_resp = client.post(
        "/v1/simulations/run",
        json={
            "num_agents": 1,
            "num_turns": 1,
            "metric_keys": ["turn.actions.counts_by_type", "unknown.metric"],
        },
    )
    assert create_resp.status_code == 422


def test_post_run_with_empty_metric_keys_returns_422(simulation_client):
    """POST with empty metric_keys returns 422; omit the field or use valid keys."""
    client, fastapi_app = simulation_client
    fastapi_app.state.engine = _make_mock_engine_with_metric_keys()
    create_resp = client.post(
        "/v1/simulations/run",
        json={
            "num_agents": 1,
            "num_turns": 1,
            "metric_keys": [],
        },
    )
    assert create_resp.status_code == 422
