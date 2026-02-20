"""Tests for GET /v1/simulations/config/default."""

from fastapi.testclient import TestClient

from simulation.api.main import app


def test_get_config_default_returns_200_and_expected_shape():
    """GET /v1/simulations/config/default returns 200 and default config."""
    with TestClient(app) as client:
        response = client.get("/v1/simulations/config/default")
        assert response.status_code == 200
        data = response.json()
        assert data == {"num_agents": 5, "num_turns": 10}
        assert isinstance(data["num_agents"], int)
        assert isinstance(data["num_turns"], int)
