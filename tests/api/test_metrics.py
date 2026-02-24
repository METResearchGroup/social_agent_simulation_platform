"""Tests for GET /v1/simulations/metrics endpoint."""

BUILTIN_METRIC_KEYS: set[str] = {
    "turn.actions.counts_by_type",
    "turn.actions.total",
    "run.actions.total_by_type",
    "run.actions.total",
}

EXPECTED_METRICS: dict[str, dict[str, str]] = {
    "turn.actions.counts_by_type": {
        "description": "Count of actions per turn, by action type.",
        "scope": "turn",
        "author": "platform",
    },
    "turn.actions.total": {
        "description": "Total number of actions in a turn.",
        "scope": "turn",
        "author": "platform",
    },
    "run.actions.total_by_type": {
        "description": "Aggregated action counts across all turns, by type.",
        "scope": "run",
        "author": "platform",
    },
    "run.actions.total": {
        "description": "Total number of actions in the run.",
        "scope": "run",
        "author": "platform",
    },
}


def test_get_metrics_returns_list(simulation_client):
    """GET /v1/simulations/metrics returns 200 with a list of at least 4 items."""
    client, _ = simulation_client
    response = client.get("/v1/simulations/metrics")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 4


def test_get_metrics_includes_builtins(simulation_client):
    """Each builtin metric is present with expected description, scope, author."""
    client, _ = simulation_client
    response = client.get("/v1/simulations/metrics")

    assert response.status_code == 200
    data = response.json()
    by_key = {m["key"]: m for m in data}

    for key in BUILTIN_METRIC_KEYS:
        assert key in by_key, f"Missing metric: {key}"
        metric = by_key[key]
        expected = EXPECTED_METRICS[key]
        assert metric["description"] == expected["description"]
        assert metric["scope"] == expected["scope"]
        assert metric["author"] == expected["author"]


def test_get_metrics_ordering_deterministic(simulation_client):
    """Result is sorted by key."""
    client, _ = simulation_client
    response = client.get("/v1/simulations/metrics")

    assert response.status_code == 200
    data = response.json()
    keys = [m["key"] for m in data]
    assert keys == sorted(keys)


def test_get_metrics_schema_shape(simulation_client):
    """Each item has key, description, scope, author as strings; scope in turn|run."""
    client, _ = simulation_client
    response = client.get("/v1/simulations/metrics")

    assert response.status_code == 200
    data = response.json()
    valid_scopes: set[str] = {"turn", "run"}

    for item in data:
        assert "key" in item
        assert "description" in item
        assert "scope" in item
        assert "author" in item
        assert isinstance(item["key"], str)
        assert isinstance(item["description"], str)
        assert isinstance(item["scope"], str)
        assert isinstance(item["author"], str)
        assert item["scope"] in valid_scopes
