"""Tests for agent API endpoints."""

import uuid

from simulation.api.constants import DEFAULT_AGENT_LIST_LIMIT
from simulation.core.models.agent import PersonaSource
from tests.factories import AgentRecordFactory


def test_get_simulations_agents_returns_list(simulation_client, temp_db):
    """GET /v1/simulations/agents returns 200 with list (DB may be empty)."""
    client, _ = simulation_client
    response = client.get("/v1/simulations/agents")

    expected_result = {"status_code": 200}
    assert response.status_code == expected_result["status_code"]
    data = response.json()
    assert isinstance(data, list)


def test_get_simulations_agents_matches_db_and_sorted(
    simulation_client, temp_db, agent_repo
):
    """GET /v1/simulations/agents returns DB-backed agents sorted newest-first."""
    # Seed the temp DB in non-sorted order so ordering assertions are meaningful.
    agent_repo.create_or_update_agent(
        AgentRecordFactory.create(
            agent_id="did:plc:z",
            handle="@z.bsky.social",
            persona_source=PersonaSource.SYNC_BLUESKY,
            display_name="@z.bsky.social",
            created_at="2026_02_25-10:00:00",
            updated_at="2026_02_25-10:00:00",
        ),
    )
    agent_repo.create_or_update_agent(
        AgentRecordFactory.create(
            agent_id="did:plc:a",
            handle="@a.bsky.social",
            persona_source=PersonaSource.SYNC_BLUESKY,
            display_name="@a.bsky.social",
            created_at="2026_02_24-10:00:00",
            updated_at="2026_02_24-10:00:00",
        ),
    )

    client, _ = simulation_client
    response = client.get("/v1/simulations/agents")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    handles = [a["handle"] for a in data]

    expected_handles = ["@z.bsky.social", "@a.bsky.social"]
    assert handles == expected_handles


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
    simulation_client, temp_db, agent_repo
):
    """POST agent then GET /agents returns the new agent newest-first."""
    agent_repo.create_or_update_agent(
        AgentRecordFactory.create(
            agent_id="did:plc:existing",
            handle="@existing.bsky.social",
            persona_source=PersonaSource.SYNC_BLUESKY,
            display_name="@existing.bsky.social",
            created_at="2026_02_24-10:00:00",
            updated_at="2026_02_24-10:00:00",
        ),
    )
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

    get_resp = client.get("/v1/simulations/agents?limit=5&offset=0")
    expected_result = {"status_code": 200}
    assert get_resp.status_code == expected_result["status_code"]
    agents = get_resp.json()
    handles = [a["handle"] for a in agents]
    assert handles[0] == created["handle"]


def test_get_simulations_agents_pagination(simulation_client, temp_db, agent_repo):
    """GET /v1/simulations/agents supports limit/offset pagination."""
    repo = agent_repo
    for handle, agent_id in [
        ("@c.bsky.social", "did:plc:c"),
        ("@a.bsky.social", "did:plc:a"),
        ("@b.bsky.social", "did:plc:b"),
    ]:
        repo.create_or_update_agent(
            AgentRecordFactory.create(
                agent_id=agent_id,
                handle=handle,
                persona_source=PersonaSource.SYNC_BLUESKY,
                display_name=handle,
                created_at="2026_02_24-10:00:00",
                updated_at="2026_02_24-10:00:00",
            ),
        )

    client, _ = simulation_client
    r1 = client.get("/v1/simulations/agents?limit=2&offset=0")
    assert r1.status_code == 200
    data1 = r1.json()
    assert [a["handle"] for a in data1] == ["@a.bsky.social", "@b.bsky.social"]

    r2 = client.get("/v1/simulations/agents?limit=2&offset=2")
    assert r2.status_code == 200
    data2 = r2.json()
    assert [a["handle"] for a in data2] == ["@c.bsky.social"]


def test_get_simulations_agents_query_case_insensitive_substring(
    simulation_client, temp_db, agent_repo
):
    """GET /v1/simulations/agents?q supports case-insensitive substring matching on handle."""
    agent_repo.create_or_update_agent(
        AgentRecordFactory.create(
            agent_id="did:plc:alpha",
            handle="@alpha.bsky.social",
            persona_source=PersonaSource.SYNC_BLUESKY,
            display_name="@alpha.bsky.social",
            created_at="2026_02_24-10:00:00",
            updated_at="2026_02_24-10:00:00",
        ),
    )
    agent_repo.create_or_update_agent(
        AgentRecordFactory.create(
            agent_id="did:plc:beta",
            handle="@beta.bsky.social",
            persona_source=PersonaSource.SYNC_BLUESKY,
            display_name="@beta.bsky.social",
            created_at="2026_02_24-10:00:00",
            updated_at="2026_02_24-10:00:00",
        ),
    )

    client, _ = simulation_client
    response = client.get("/v1/simulations/agents?q=ALPHA&limit=100&offset=0")
    expected_result = {"status_code": 200, "handles": ["@alpha.bsky.social"]}
    assert response.status_code == expected_result["status_code"]
    data = response.json()
    assert [a["handle"] for a in data] == expected_result["handles"]


def test_get_simulations_agents_query_too_long_returns_422(simulation_client, temp_db):
    """q longer than 200 characters yields 422 with stable error shape."""
    client, _ = simulation_client
    q = "a" * 201

    response = client.get(f"/v1/simulations/agents?q={q}&limit=100&offset=0")
    expected_result = {"status_code": 422, "error_code": "VALIDATION_ERROR"}
    assert response.status_code == expected_result["status_code"]
    err = response.json()
    assert err["error"]["code"] == expected_result["error_code"]


def test_get_simulations_agents_query_whitespace_only_returns_all(
    simulation_client, temp_db, agent_repo
):
    """Whitespace-only q is treated as unset (no filtering)."""
    for handle, agent_id in [
        ("@alpha.bsky.social", "did:plc:alpha"),
        ("@beta.bsky.social", "did:plc:beta"),
    ]:
        agent_repo.create_or_update_agent(
            AgentRecordFactory.create(
                agent_id=agent_id,
                handle=handle,
                persona_source=PersonaSource.SYNC_BLUESKY,
                display_name=handle,
                created_at="2026_02_24-10:00:00",
                updated_at="2026_02_24-10:00:00",
            ),
        )

    client, _ = simulation_client
    response = client.get("/v1/simulations/agents?q=%20%20&limit=100&offset=0")
    expected_result = {"status_code": 200}
    assert response.status_code == expected_result["status_code"]
    data = response.json()
    handles = [a["handle"] for a in data]

    expected_handles = ["@alpha.bsky.social", "@beta.bsky.social"]
    for handle in expected_handles:
        assert handle in handles


def test_get_simulations_agents_query_wildcards(simulation_client, temp_db, agent_repo):
    """GET /v1/simulations/agents?q supports * and ? wildcards on handle."""
    for handle, agent_id in [
        ("@alpha.bsky.social", "did:plc:alpha"),
        ("@alxha.bsky.social", "did:plc:alxha"),
        ("@beta.bsky.social", "did:plc:beta"),
    ]:
        agent_repo.create_or_update_agent(
            AgentRecordFactory.create(
                agent_id=agent_id,
                handle=handle,
                persona_source=PersonaSource.SYNC_BLUESKY,
                display_name=handle,
                created_at="2026_02_24-10:00:00",
                updated_at="2026_02_24-10:00:00",
            ),
        )

    client, _ = simulation_client
    r1 = client.get("/v1/simulations/agents?q=a*social&limit=100&offset=0")
    expected_result = {
        "status_code": 200,
        "handles": ["@alpha.bsky.social", "@alxha.bsky.social", "@beta.bsky.social"],
    }
    assert r1.status_code == expected_result["status_code"]
    assert [a["handle"] for a in r1.json()] == expected_result["handles"]

    r2 = client.get("/v1/simulations/agents?q=al?ha&limit=100&offset=0")
    expected_result = {
        "status_code": 200,
        "handles": ["@alpha.bsky.social", "@alxha.bsky.social"],
    }
    assert r2.status_code == expected_result["status_code"]
    assert [a["handle"] for a in r2.json()] == expected_result["handles"]


def test_get_simulations_agents_query_like_metacharacters(
    simulation_client, temp_db, agent_repo
):
    """SQL LIKE metacharacters are treated as literals (% _ \\) in q."""
    for handle, agent_id in [
        ("@has%percent.bsky.social", "did:plc:percent"),
        ("@has_under_score.bsky.social", "did:plc:underscore"),
        (r"@has\backslash.bsky.social", "did:plc:backslash"),
        ("@control.bsky.social", "did:plc:control"),
    ]:
        agent_repo.create_or_update_agent(
            AgentRecordFactory.create(
                agent_id=agent_id,
                handle=handle,
                persona_source=PersonaSource.SYNC_BLUESKY,
                display_name=handle,
                created_at="2026_02_24-10:00:00",
                updated_at="2026_02_24-10:00:00",
            ),
        )

    client, _ = simulation_client

    r_percent = client.get("/v1/simulations/agents?q=%25&limit=100&offset=0")
    expected_result = {"status_code": 200, "handles": ["@has%percent.bsky.social"]}
    assert r_percent.status_code == expected_result["status_code"]
    assert [a["handle"] for a in r_percent.json()] == expected_result["handles"]

    r_underscore = client.get("/v1/simulations/agents?q=_&limit=100&offset=0")
    expected_result = {"status_code": 200, "handles": ["@has_under_score.bsky.social"]}
    assert r_underscore.status_code == expected_result["status_code"]
    assert [a["handle"] for a in r_underscore.json()] == expected_result["handles"]

    r_backslash = client.get("/v1/simulations/agents?q=%5C&limit=100&offset=0")
    expected_result = {"status_code": 200, "handles": [r"@has\backslash.bsky.social"]}
    assert r_backslash.status_code == expected_result["status_code"]
    assert [a["handle"] for a in r_backslash.json()] == expected_result["handles"]


def test_get_simulations_agents_query_pagination(
    simulation_client, temp_db, agent_repo
):
    """GET /v1/simulations/agents?q supports pagination with deterministic ordering."""
    for handle, agent_id in [
        ("@c.bsky.social", "did:plc:c"),
        ("@a.bsky.social", "did:plc:a"),
        ("@b.bsky.social", "did:plc:b"),
    ]:
        agent_repo.create_or_update_agent(
            AgentRecordFactory.create(
                agent_id=agent_id,
                handle=handle,
                persona_source=PersonaSource.SYNC_BLUESKY,
                display_name=handle,
                created_at="2026_02_24-10:00:00",
                updated_at="2026_02_24-10:00:00",
            ),
        )

    client, _ = simulation_client
    response = client.get("/v1/simulations/agents?q=bsky&limit=2&offset=1")
    expected_result = {
        "status_code": 200,
        "handles": ["@b.bsky.social", "@c.bsky.social"],
    }
    assert response.status_code == expected_result["status_code"]
    data = response.json()
    assert [a["handle"] for a in data] == expected_result["handles"]


def test_get_simulations_agents_query_scrubbing(simulation_client, temp_db, agent_repo):
    """Whitespace in q is scrubbed so '  a  ' behaves like 'a'."""
    for handle, agent_id in [
        ("@alpha.bsky.social", "did:plc:alpha"),
        ("@beta.bsky.social", "did:plc:beta"),
    ]:
        agent_repo.create_or_update_agent(
            AgentRecordFactory.create(
                agent_id=agent_id,
                handle=handle,
                persona_source=PersonaSource.SYNC_BLUESKY,
                display_name=handle,
                created_at="2026_02_24-10:00:00",
                updated_at="2026_02_24-10:00:00",
            ),
        )

    client, _ = simulation_client
    response = client.get(
        "/v1/simulations/agents?q=%20%20ALPHA%20%20&limit=100&offset=0"
    )
    expected_result = {"status_code": 200, "handles": ["@alpha.bsky.social"]}
    assert response.status_code == expected_result["status_code"]
    data = response.json()
    assert [a["handle"] for a in data] == expected_result["handles"]


def test_get_simulations_agents_default_limit_is_100(
    simulation_client, temp_db, agent_repo
):
    """GET /v1/simulations/agents defaults to DEFAULT_AGENT_LIST_LIMIT when no params are provided."""
    repo = agent_repo
    total_agents = DEFAULT_AGENT_LIST_LIMIT + 5
    for i in range(total_agents):
        handle = f"@user{i:03d}.bsky.social"
        repo.create_or_update_agent(
            AgentRecordFactory.create(
                agent_id=f"did:plc:{i:03d}",
                handle=handle,
                persona_source=PersonaSource.SYNC_BLUESKY,
                display_name=handle,
                created_at="2026_02_24-10:00:00",
                updated_at="2026_02_24-10:00:00",
            ),
        )

    client, _ = simulation_client
    r = client.get("/v1/simulations/agents")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == DEFAULT_AGENT_LIST_LIMIT


def test_get_simulations_agents_pagination_validation_errors(
    simulation_client, temp_db
):
    """Invalid limit/offset yield 422 with stable error shape."""
    client, _ = simulation_client

    r1 = client.get("/v1/simulations/agents?offset=-1")
    assert r1.status_code == 422
    err1 = r1.json()
    assert err1["error"]["code"] == "VALIDATION_ERROR"

    r2 = client.get("/v1/simulations/agents?limit=0")
    assert r2.status_code == 422
    err2 = r2.json()
    assert err2["error"]["code"] == "VALIDATION_ERROR"

    r3 = client.get("/v1/simulations/agents?limit=999999")
    assert r3.status_code == 422
    err3 = r3.json()
    assert err3["error"]["code"] == "VALIDATION_ERROR"


def test_delete_simulations_agents_success_removes_agent(simulation_client, temp_db):
    """DELETE /v1/simulations/agents removes agent and returns 204."""
    client, _ = simulation_client
    handle = f"del-{uuid.uuid4().hex[:8]}.bsky.social"
    body = {
        "handle": handle,
        "display_name": "Delete Me",
        "bio": "Temporary",
    }

    post_resp = client.post("/v1/simulations/agents", json=body)
    assert post_resp.status_code == 201
    created = post_resp.json()

    delete_resp = client.delete(f"/v1/simulations/agents/{created['handle']}")
    assert delete_resp.status_code == 204

    get_resp = client.get("/v1/simulations/agents?limit=100&offset=0")
    assert get_resp.status_code == 200
    handles = [agent["handle"] for agent in get_resp.json()]
    assert created["handle"] not in handles


def test_delete_simulations_agents_missing_returns_404(simulation_client, temp_db):
    """DELETE /v1/simulations/agents returns 404 for unknown handle."""
    client, _ = simulation_client
    missing_handle = "@missing.bsky.social"

    resp = client.delete(f"/v1/simulations/agents/{missing_handle}")
    assert resp.status_code == 404
    err = resp.json()
    assert err["error"]["code"] == "AGENT_NOT_FOUND"
