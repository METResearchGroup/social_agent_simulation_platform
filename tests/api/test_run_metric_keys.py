"""Tests for metric_keys in run request and run details."""

from lib.timestamp_utils import get_current_timestamp
from simulation.core.metrics.defaults import (
    DEFAULT_RUN_METRIC_KEYS,
    DEFAULT_TURN_METRIC_KEYS,
    get_default_metric_keys,
)
from tests.factories import EngineFactory


def test_post_run_with_metric_keys_returns_details_with_keys(simulation_client):
    """POST with metric_keys returns run; GET details includes those keys in config."""
    client, fastapi_app = simulation_client
    custom_keys = [
        "turn.actions.counts_by_type",
        "turn.actions.total",
        "run.actions.total",
    ]
    fastapi_app.state.engine = EngineFactory.create_completed_run_engine(
        run_id="run-metrics-test",
        total_turns=1,
        total_agents=1,
        metric_keys=custom_keys,
        created_at=get_current_timestamp(),
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
    default_keys = get_default_metric_keys()
    fastapi_app.state.engine = EngineFactory.create_completed_run_engine(
        run_id="run-metrics-test",
        total_turns=1,
        total_agents=1,
        metric_keys=default_keys,
        created_at=get_current_timestamp(),
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
    default_keys = sorted(set(DEFAULT_TURN_METRIC_KEYS + DEFAULT_RUN_METRIC_KEYS))
    fastapi_app.state.engine = EngineFactory.create_completed_run_engine(
        run_id="run-metrics-test",
        total_turns=1,
        total_agents=1,
        metric_keys=default_keys,
        created_at=get_current_timestamp(),
    )
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
    default_keys = sorted(set(DEFAULT_TURN_METRIC_KEYS + DEFAULT_RUN_METRIC_KEYS))
    fastapi_app.state.engine = EngineFactory.create_completed_run_engine(
        run_id="run-metrics-test",
        total_turns=1,
        total_agents=1,
        metric_keys=default_keys,
        created_at=get_current_timestamp(),
    )
    create_resp = client.post(
        "/v1/simulations/run",
        json={
            "num_agents": 1,
            "num_turns": 1,
            "metric_keys": [],
        },
    )
    assert create_resp.status_code == 422
