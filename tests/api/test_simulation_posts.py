"""Tests for GET /v1/simulations/posts endpoint."""

from simulation.api.dummy_data import DUMMY_POSTS


def test_get_simulations_posts_returns_all_when_no_uris(simulation_client):
    """GET /v1/simulations/posts returns all posts when no uris query param."""
    client, _ = simulation_client
    response = client.get("/v1/simulations/posts")

    assert response.status_code == 200
    data = response.json()
    expected_result = {"count": len(DUMMY_POSTS)}
    assert len(data) == expected_result["count"]
    assert all("uri" in post for post in data)
    assert all("author_display_name" in post for post in data)
    assert all("text" in post for post in data)


def test_get_simulations_posts_returns_filtered_by_uris(simulation_client):
    """GET /v1/simulations/posts?uris=... returns only requested posts."""
    client, _ = simulation_client
    uri1 = "at://did:plc:example1/post1"
    uri2 = "at://did:plc:example2/post2"
    response = client.get(
        "/v1/simulations/posts",
        params={"uris": [uri1, uri2]},
    )

    assert response.status_code == 200
    data = response.json()
    expected_result = {"count": 2, "uris": {uri1, uri2}}
    assert len(data) == expected_result["count"]
    returned_uris = {post["uri"] for post in data}
    assert returned_uris == expected_result["uris"]


def test_get_simulations_posts_ordering_deterministic(simulation_client):
    """GET /v1/simulations/posts returns posts sorted by uri."""
    client, _ = simulation_client
    response = client.get("/v1/simulations/posts")

    assert response.status_code == 200
    data = response.json()
    uris = [post["uri"] for post in data]
    sorted_uris = sorted(uris)
    assert uris == sorted_uris
