"""Tests for agent API endpoints."""

import uuid

from simulation.api.dummy_data import DUMMY_AGENTS


def test_get_simulations_agents_returns_list(simulation_client, temp_db):
    """GET /v1/simulations/agents returns 200 with list (DB may be empty)."""
    client, _ = simulation_client
    response = client.get("/v1/simulations/agents")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_simulations_agents_ordering_deterministic(simulation_client, temp_db):
    """Result is sorted by handle when non-empty."""
    client, _ = simulation_client
    response = client.get("/v1/simulations/agents")

    assert response.status_code == 200
    data = response.json()
    handles = [a["handle"] for a in data]
    assert handles == sorted(handles)


def test_get_simulations_agents_fields_present(simulation_client, temp_db):
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


def test_get_simulations_agents_mock_returns_dummy(simulation_client):
    """GET /v1/simulations/agents/mock returns dummy agents."""
    client, _ = simulation_client
    response = client.get("/v1/simulations/agents/mock")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == len(DUMMY_AGENTS)
    handles = [a["handle"] for a in data]
    assert handles == sorted(handles)


def test_post_simulations_agents_success(simulation_client, temp_db):
    """POST /v1/simulations/agents returns 201 with created agent."""
    client, _ = simulation_client
    handle = f"test-{uuid.uuid4().hex[:8]}.bsky.social"
    body = {
        "handle": handle,
        "display_name": "Test Agent",
        "bio": "A test bio",
    }

    response = client.post("/v1/simulations/agents", json=body)

    assert response.status_code == 201
    data = response.json()
    expected_handle = f"@{handle.lstrip('@').lower()}"
    assert data["handle"] == expected_handle
    assert data["name"] == "Test Agent"
    assert data["bio"] == "A test bio"
    assert data["generated_bio"] == ""
    assert data["followers"] == 0
    assert data["following"] == 0
    assert data["posts_count"] == 0


def test_post_simulations_agents_duplicate_handle_returns_409(
    simulation_client, temp_db
):
    """POST /v1/simulations/agents with existing handle returns 409."""
    client, _ = simulation_client
    handle = f"dup-{uuid.uuid4().hex[:8]}.bsky.social"
    body = {"handle": handle, "display_name": "First", "bio": ""}

    r1 = client.post("/v1/simulations/agents", json=body)
    assert r1.status_code == 201

    r2 = client.post("/v1/simulations/agents", json=body)
    assert r2.status_code == 409
    err = r2.json()
    assert "error" in err
    assert err["error"]["code"] == "HANDLE_ALREADY_EXISTS"


def test_post_simulations_agents_validation_empty_handle_returns_422(
    simulation_client,
):
    """POST /v1/simulations/agents with empty handle returns 422."""
    client, _ = simulation_client
    response = client.post(
        "/v1/simulations/agents",
        json={"handle": "", "display_name": "Name", "bio": ""},
    )
    assert response.status_code == 422


def test_post_simulations_agents_validation_empty_display_name_returns_422(
    simulation_client,
):
    """POST /v1/simulations/agents with empty display_name returns 422."""
    client, _ = simulation_client
    response = client.post(
        "/v1/simulations/agents",
        json={"handle": "user.bsky.social", "display_name": "", "bio": ""},
    )
    assert response.status_code == 422


def test_post_simulations_agents_then_get_includes_new_agent(
    simulation_client, temp_db
):
    """POST agent then GET /agents includes the new agent."""
    client, _ = simulation_client
    handle = f"new-{uuid.uuid4().hex[:8]}.bsky.social"
    body = {
        "handle": handle,
        "display_name": "New Agent",
        "bio": "Created via API",
    }

    post_resp = client.post("/v1/simulations/agents", json=body)
    assert post_resp.status_code == 201
    created = post_resp.json()

    get_resp = client.get("/v1/simulations/agents")
    assert get_resp.status_code == 200
    agents = get_resp.json()
    handles = [a["handle"] for a in agents]
    assert created["handle"] in handles
