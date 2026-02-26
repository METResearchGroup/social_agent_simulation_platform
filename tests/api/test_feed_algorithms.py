"""Tests for GET /v1/simulations/feed-algorithms endpoint."""


def test_get_feed_algorithms_returns_list(simulation_client):
    """GET /v1/simulations/feed-algorithms returns 200 with list of algorithms."""
    client, _ = simulation_client
    response = client.get("/v1/simulations/feed-algorithms")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_get_feed_algorithms_includes_chronological(simulation_client):
    """Chronological algorithm is present with expected metadata."""
    client, _ = simulation_client
    response = client.get("/v1/simulations/feed-algorithms")

    assert response.status_code == 200
    data = response.json()
    chronological = next((a for a in data if a["id"] == "chronological"), None)
    expected_display_name = "Chronological"
    expected_description_snippet = "sorted by creation time"
    expected_schema_type = "object"
    expected_order_enum = ["newest_first", "oldest_first"]
    assert chronological is not None
    assert chronological["display_name"] == expected_display_name
    assert expected_description_snippet in chronological["description"]
    assert isinstance(chronological.get("config_schema"), dict)
    config_schema = chronological["config_schema"]
    assert config_schema["type"] == expected_schema_type
    assert "order" in config_schema["properties"]
    assert config_schema["properties"]["order"]["enum"] == expected_order_enum
