"""Tests for agent API endpoints."""

import uuid

from simulation.api.constants import DEFAULT_AGENT_LIST_LIMIT
from simulation.core.models.agent import Agent, PersonaSource


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
    """GET /v1/simulations/agents returns DB-backed agents sorted by handle."""
    # Seed the temp DB in non-sorted order so ordering assertions are meaningful.
    agent_repo.create_or_update_agent(
        Agent(
            agent_id="did:plc:z",
            handle="@z.bsky.social",
            persona_source=PersonaSource.SYNC_BLUESKY,
            display_name="@z.bsky.social",
            created_at="2026_02_24-10:00:00",
            updated_at="2026_02_24-10:00:00",
        )
    )
    agent_repo.create_or_update_agent(
        Agent(
            agent_id="did:plc:a",
            handle="@a.bsky.social",
            persona_source=PersonaSource.SYNC_BLUESKY,
            display_name="@a.bsky.social",
            created_at="2026_02_24-10:00:00",
            updated_at="2026_02_24-10:00:00",
        )
    )

    client, _ = simulation_client
    response = client.get("/v1/simulations/agents")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    handles = [a["handle"] for a in data]

    expected_handles = ["@a.bsky.social", "@z.bsky.social"]
    assert handles == expected_handles
    assert handles == sorted(handles)


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


def test_post_simulations_agents_persists_seed_actions(
    simulation_client,
    temp_db,
    agent_seed_like_repo,
    agent_seed_comment_repo,
    agent_seed_follow_repo,
):
    """POST /v1/simulations/agents persists seed likes/comments/follows when provided."""
    client, _ = simulation_client
    handle = f"seed-{uuid.uuid4().hex[:8]}.bsky.social"
    body = {
        "handle": handle,
        "display_name": "Seed Agent",
        "bio": "Bio",
        "liked_post_uris": [
            "  at://did:plc:example/app.bsky.feed.post/123  ",
            "",  # ignored
            "at://did:plc:example/app.bsky.feed.post/123",  # dup ignored
        ],
        "comments": [
            {
                "text": "  hello  ",
                "post_uri": " at://did:plc:example/app.bsky.feed.post/999 ",
            },
            {
                "text": "   ",
                "post_uri": "at://did:plc:example/app.bsky.feed.post/should_skip",
            },
        ],
        "linked_agent_handles": [
            "Other.BSKY.social",
            "@other.bsky.social",  # dup after normalization
            handle,  # self-follow ignored after normalization
        ],
    }

    resp = client.post("/v1/simulations/agents", json=body)
    assert resp.status_code == 201
    created = resp.json()
    created_handle = created["handle"]

    seed_likes = agent_seed_like_repo.read_agent_seed_likes_by_agent_handles(
        [created_handle]
    )
    assert len(seed_likes) == 1
    assert seed_likes[0].agent_handle == created_handle
    assert seed_likes[0].post_uri == "at://did:plc:example/app.bsky.feed.post/123"

    seed_comments = agent_seed_comment_repo.read_agent_seed_comments_by_agent_handles(
        [created_handle]
    )
    assert len(seed_comments) == 1
    assert seed_comments[0].agent_handle == created_handle
    assert seed_comments[0].text == "hello"
    assert seed_comments[0].post_uri == "at://did:plc:example/app.bsky.feed.post/999"

    seed_follows = agent_seed_follow_repo.read_agent_seed_follows_by_agent_handles(
        [created_handle]
    )
    assert len(seed_follows) == 1
    assert seed_follows[0].agent_handle == created_handle
    assert seed_follows[0].user_id == "@other.bsky.social"


def test_get_simulations_agents_pagination(simulation_client, temp_db, agent_repo):
    """GET /v1/simulations/agents supports limit/offset pagination."""
    repo = agent_repo
    for handle, agent_id in [
        ("@c.bsky.social", "did:plc:c"),
        ("@a.bsky.social", "did:plc:a"),
        ("@b.bsky.social", "did:plc:b"),
    ]:
        repo.create_or_update_agent(
            Agent(
                agent_id=agent_id,
                handle=handle,
                persona_source=PersonaSource.SYNC_BLUESKY,
                display_name=handle,
                created_at="2026_02_24-10:00:00",
                updated_at="2026_02_24-10:00:00",
            )
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


def test_get_simulations_agents_default_limit_is_100(
    simulation_client, temp_db, agent_repo
):
    """GET /v1/simulations/agents defaults to DEFAULT_AGENT_LIST_LIMIT when no params are provided."""
    repo = agent_repo
    total_agents = DEFAULT_AGENT_LIST_LIMIT + 5
    for i in range(total_agents):
        handle = f"@user{i:03d}.bsky.social"
        repo.create_or_update_agent(
            Agent(
                agent_id=f"did:plc:{i:03d}",
                handle=handle,
                persona_source=PersonaSource.SYNC_BLUESKY,
                display_name=handle,
                created_at="2026_02_24-10:00:00",
                updated_at="2026_02_24-10:00:00",
            )
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
