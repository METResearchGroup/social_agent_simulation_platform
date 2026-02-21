"""Tests for GET /v1/simulations/config/default."""


def test_get_config_default_returns_200_and_expected_shape(simulation_client):
    """GET /v1/simulations/config/default returns 200 and default config."""
    client, _ = simulation_client
    response = client.get("/v1/simulations/config/default")
    assert response.status_code == 200
    data = response.json()
    assert data == {"num_agents": 5, "num_turns": 10}
    assert isinstance(data["num_agents"], int)
    assert isinstance(data["num_turns"], int)
