"""Tests for GET /v1/simulations/posts endpoint."""

from simulation.core.models.posts import BlueskyFeedPost


def _make_post(*, uri: str, text: str) -> BlueskyFeedPost:
    return BlueskyFeedPost(
        id=uri,
        uri=uri,
        author_display_name="Test Author",
        author_handle="test.author",
        text=text,
        like_count=1,
        bookmark_count=0,
        quote_count=0,
        reply_count=0,
        repost_count=0,
        created_at="2026-01-01T00:00:00.000Z",
    )


def test_get_simulations_posts_returns_all_when_no_uris(
    simulation_client,
    feed_post_repo,
):
    """GET /v1/simulations/posts returns all posts when no uris query param."""
    post_1 = _make_post(uri="at://did:plc:example1/post1", text="hello 1")
    post_2 = _make_post(uri="at://did:plc:example2/post2", text="hello 2")
    feed_post_repo.create_or_update_feed_posts([post_1, post_2])

    client, _ = simulation_client
    response = client.get("/v1/simulations/posts")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all("uri" in post for post in data)
    assert all("author_display_name" in post for post in data)
    assert all("text" in post for post in data)


def test_get_simulations_posts_returns_filtered_by_uris(
    simulation_client,
    feed_post_repo,
):
    """GET /v1/simulations/posts?uris=... returns only requested posts."""
    uri1 = "at://did:plc:example1/post1"
    uri2 = "at://did:plc:example2/post2"
    feed_post_repo.create_or_update_feed_posts(
        [
            _make_post(uri=uri1, text="hello 1"),
            _make_post(uri=uri2, text="hello 2"),
        ]
    )

    client, _ = simulation_client
    response = client.get(
        "/v1/simulations/posts",
        params={"uris": [uri1, uri2]},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    returned_uris = {post["uri"] for post in data}
    assert returned_uris == {uri1, uri2}


def test_get_simulations_posts_ordering_deterministic(
    simulation_client,
    feed_post_repo,
):
    """GET /v1/simulations/posts returns posts sorted by uri."""
    feed_post_repo.create_or_update_feed_posts(
        [
            _make_post(uri="at://did:plc:b/post2", text="b"),
            _make_post(uri="at://did:plc:a/post1", text="a"),
        ]
    )

    client, _ = simulation_client
    response = client.get("/v1/simulations/posts")

    assert response.status_code == 200
    data = response.json()
    uris = [post["uri"] for post in data]
    sorted_uris = sorted(uris)
    assert uris == sorted_uris
