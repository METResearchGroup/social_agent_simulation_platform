"""Tests for GET /v1/simulations/agents endpoint."""

from simulation.api.dummy_data import DUMMY_AGENTS


def test_get_simulations_agents_returns_list(simulation_client):
    """GET /v1/simulations/agents returns 200 with list of agents."""
    client, _ = simulation_client
    response = client.get("/v1/simulations/agents")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == len(DUMMY_AGENTS)


def test_get_simulations_agents_ordering_deterministic(simulation_client):
    """Result is sorted by handle."""
    client, _ = simulation_client
    response = client.get("/v1/simulations/agents")

    assert response.status_code == 200
    data = response.json()
    handles = [a["handle"] for a in data]
    assert handles == sorted(handles)


def test_get_simulations_agents_fields_present(simulation_client):
    """Each agent has handle, name, bio, generated_bio, followers, following, posts_count."""
    client, _ = simulation_client
    response = client.get("/v1/simulations/agents")

    assert response.status_code == 200
    data = response.json()
    required_fields = {
        "handle",
        "name",
        "bio",
        "generated_bio",
        "followers",
        "following",
        "posts_count",
    }
    for agent in data:
        for field in required_fields:
            assert field in agent, f"Agent missing field {field}"
