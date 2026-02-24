"""Tests for agent API endpoints."""

import uuid

from simulation.api.dummy_data import DUMMY_AGENTS


def test_get_simulations_agents_returns_list(simulation_client, temp_db):
    """GET /v1/simulations/agents returns 200 with list (DB may be empty)."""
    client, _ = simulation_client
    response = client.get("/v1/simulations/agents")

    expected_result = {"status_code": 200}
    assert response.status_code == expected_result["status_code"]
    data = response.json()
    assert isinstance(data, list)


def test_get_simulations_agents_ordering_deterministic(simulation_client, temp_db):
    """Result is sorted by handle when non-empty."""
    client, _ = simulation_client
    response = client.get("/v1/simulations/agents")

    expected_result = {"status_code": 200}
    assert response.status_code == expected_result["status_code"]
    data = response.json()
    handles = [a["handle"] for a in data]
    expected_result = sorted(handles)
    assert handles == expected_result


def test_get_simulations_agents_fields_present(simulation_client, temp_db):
    """Each agent has handle, name, bio, generated_bio, followers, following, posts_count."""
    client, _ = simulation_client
    response = client.get("/v1/simulations/agents")

    expected_result = {"status_code": 200}
    assert response.status_code == expected_result["status_code"]
    data = response.json()
    expected_result = {
        "handle",
        "name",
        "bio",
        "generated_bio",
        "followers",
        "following",
        "posts_count",
    }
    for agent in data:
        for field in expected_result:
            assert field in agent, f"Agent missing field {field}"


def test_get_simulations_agents_mock_returns_dummy(simulation_client):
    """GET /v1/simulations/agents/mock returns dummy agents."""
    client, _ = simulation_client
    response = client.get("/v1/simulations/agents/mock")

    expected_result = {"status_code": 200, "count": len(DUMMY_AGENTS)}
    assert response.status_code == expected_result["status_code"]
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == expected_result["count"]
    handles = [a["handle"] for a in data]
    expected_result = sorted(handles)
    assert handles == expected_result


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

    expected_result = {
        "status_code": 201,
        "name": "Test Agent",
        "bio": "A test bio",
        "generated_bio": "",
        "followers": 0,
        "following": 0,
        "posts_count": 0,
    }
    assert response.status_code == expected_result["status_code"]
    data = response.json()
    expected_result["handle"] = f"@{handle.lstrip('@').lower()}"
    assert data["handle"] == expected_result["handle"]
    assert data["name"] == expected_result["name"]
    assert data["bio"] == expected_result["bio"]
    assert data["generated_bio"] == expected_result["generated_bio"]
    assert data["followers"] == expected_result["followers"]
    assert data["following"] == expected_result["following"]
    assert data["posts_count"] == expected_result["posts_count"]


def test_post_simulations_agents_duplicate_handle_returns_409(
    simulation_client, temp_db
):
    """POST /v1/simulations/agents with existing handle returns 409."""
    client, _ = simulation_client
    handle = f"dup-{uuid.uuid4().hex[:8]}.bsky.social"
    body = {"handle": handle, "display_name": "First", "bio": ""}

    r1 = client.post("/v1/simulations/agents", json=body)
    expected_result = {"status_code": 201}
    assert r1.status_code == expected_result["status_code"]

    r2 = client.post("/v1/simulations/agents", json=body)
    expected_result = {"status_code": 409, "error_code": "HANDLE_ALREADY_EXISTS"}
    assert r2.status_code == expected_result["status_code"]
    err = r2.json()
    assert "error" in err
    assert err["error"]["code"] == expected_result["error_code"]


def test_post_simulations_agents_validation_empty_handle_returns_422(
    simulation_client,
):
    """POST /v1/simulations/agents with empty handle returns 422."""
    client, _ = simulation_client
    response = client.post(
        "/v1/simulations/agents",
        json={"handle": "", "display_name": "Name", "bio": ""},
    )
    expected_result = {"status_code": 422}
    assert response.status_code == expected_result["status_code"]


def test_post_simulations_agents_validation_empty_display_name_returns_422(
    simulation_client,
):
    """POST /v1/simulations/agents with empty display_name returns 422."""
    client, _ = simulation_client
    response = client.post(
        "/v1/simulations/agents",
        json={"handle": "user.bsky.social", "display_name": "", "bio": ""},
    )
    expected_result = {"status_code": 422}
    assert response.status_code == expected_result["status_code"]


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
    expected_result = {"status_code": 201}
    assert post_resp.status_code == expected_result["status_code"]
    created = post_resp.json()

    get_resp = client.get("/v1/simulations/agents")
    expected_result = {"status_code": 200}
    assert get_resp.status_code == expected_result["status_code"]
    agents = get_resp.json()
    handles = [a["handle"] for a in agents]
    expected_result = created["handle"]
    assert expected_result in handles
    assert created["handle"] in handles


def test_post_simulations_agents_with_comments_likes_linked(simulation_client, temp_db):
    """POST with comments, liked_post_uris, linked_agent_handles persists and GET returns them."""
    client, _ = simulation_client
    base_handle = f"base-{uuid.uuid4().hex[:8]}.bsky.social"
    linkee_handle = f"linkee-{uuid.uuid4().hex[:8]}.bsky.social"

    base_resp = client.post(
        "/v1/simulations/agents",
        json={"handle": base_handle, "display_name": "Base", "bio": ""},
    )
    assert base_resp.status_code == 201

    linkee_resp = client.post(
        "/v1/simulations/agents",
        json={"handle": linkee_handle, "display_name": "Linkee", "bio": ""},
    )
    assert linkee_resp.status_code == 201
    linkee_created = linkee_resp.json()
    linkee_normalized = linkee_created["handle"]

    creator_handle = f"creator-{uuid.uuid4().hex[:8]}.bsky.social"
    body = {
        "handle": creator_handle,
        "display_name": "Creator",
        "bio": "Has history",
        "comments": [
            {
                "text": "Great post",
                "post_uri": "at://did:plc:xyz/app.bsky.feed.post/abc",
            },
            {"text": "Another", "post_uri": "at://did:plc:xyz/app.bsky.feed.post/def"},
        ],
        "liked_post_uris": [
            "at://did:plc:xyz/app.bsky.feed.post/ghi",
            "at://did:plc:xyz/app.bsky.feed.post/jkl",
        ],
        "linked_agent_handles": [linkee_normalized],
    }

    post_resp = client.post("/v1/simulations/agents", json=body)
    assert post_resp.status_code == 201
    created = post_resp.json()
    assert created["handle"] == f"@{creator_handle.lstrip('@').lower()}"
    assert len(created.get("comments", [])) == 2
    assert len(created.get("liked_post_uris", [])) == 2
    assert created.get("linked_agent_handles", []) == [linkee_normalized]

    get_resp = client.get("/v1/simulations/agents")
    assert get_resp.status_code == 200
    agents = get_resp.json()
    agent_by_handle = {a["handle"]: a for a in agents}
    assert created["handle"] in agent_by_handle
    agent = agent_by_handle[created["handle"]]
    assert len(agent.get("comments", [])) == 2
    assert len(agent.get("liked_post_uris", [])) == 2
    assert len(agent.get("linked_agent_handles", [])) == 1


def test_post_simulations_agents_invalid_linked_handle_returns_422(
    simulation_client, temp_db
):
    """POST with non-existent linked_agent_handle returns 422."""
    client, _ = simulation_client
    handle = f"test-{uuid.uuid4().hex[:8]}.bsky.social"
    body = {
        "handle": handle,
        "display_name": "Test",
        "bio": "",
        "linked_agent_handles": ["@nonexistent.agent.bsky.social"],
    }

    response = client.post("/v1/simulations/agents", json=body)
    assert response.status_code == 422
    err = response.json()
    assert "error" in err
    assert err["error"]["code"] == "LINKED_AGENT_NOT_FOUND"


def test_post_simulations_agents_empty_comments_likes_succeeds(
    simulation_client, temp_db
):
    """POST with empty comments and liked_post_uris succeeds; no extra rows."""
    client, _ = simulation_client
    handle = f"empty-{uuid.uuid4().hex[:8]}.bsky.social"
    body = {
        "handle": handle,
        "display_name": "Empty History",
        "bio": "",
        "comments": [{"text": "", "post_uri": ""}],
        "liked_post_uris": ["", "  ", "\n"],
        "linked_agent_handles": [],
    }

    response = client.post("/v1/simulations/agents", json=body)
    assert response.status_code == 201
    data = response.json()
    assert data["handle"] == f"@{handle.lstrip('@').lower()}"
    assert data.get("comments", []) == []
    assert data.get("liked_post_uris", []) == []
    assert data.get("linked_agent_handles", []) == []
