"""Tests for GET /v1/simulations/config/default."""

from simulation.core.metrics.defaults import get_default_metric_keys


def test_get_config_default_returns_200_and_expected_shape(simulation_client):
    """GET /v1/simulations/config/default returns 200 and default config."""
    client, _ = simulation_client
    response = client.get("/v1/simulations/config/default")
    assert response.status_code == 200
    data = response.json()
    expected_result = {
        "num_agents": 5,
        "num_turns": 10,
        "metric_keys": get_default_metric_keys(),
    }
    assert data == expected_result
    assert isinstance(data["num_agents"], int)
    assert isinstance(data["num_turns"], int)
    assert isinstance(data["metric_keys"], list)
    assert len(data["metric_keys"]) > 0
    assert all(isinstance(k, str) for k in data["metric_keys"])
