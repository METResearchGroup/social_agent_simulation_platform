"""Tests for GET /v1/simulations/metrics endpoint."""

BUILTIN_METRIC_KEYS: set[str] = {
    "turn.actions.counts_by_type",
    "turn.actions.total",
    "run.actions.total_by_type",
    "run.actions.total",
}

EXPECTED_METRICS: dict[str, dict[str, str]] = {
    "turn.actions.counts_by_type": {
        "display_name": "Actions by type (turn)",
        "description": "Count of actions per turn, by action type.",
        "scope": "turn",
        "author": "platform",
    },
    "turn.actions.total": {
        "display_name": "Total actions (turn)",
        "description": "Total number of actions in a turn.",
        "scope": "turn",
        "author": "platform",
    },
    "run.actions.total_by_type": {
        "display_name": "Actions by type (run)",
        "description": "Aggregated action counts across all turns, by type.",
        "scope": "run",
        "author": "platform",
    },
    "run.actions.total": {
        "display_name": "Total actions (run)",
        "description": "Total number of actions in the run.",
        "scope": "run",
        "author": "platform",
    },
}


def test_get_metrics_returns_list(simulation_client):
    """GET /v1/simulations/metrics returns 200 with a list of at least 4 items."""
    client, _ = simulation_client
    response = client.get("/v1/simulations/metrics")

    expected_result = {
        "status_code": 200,
        "min_items": 4,
    }
    assert response.status_code == expected_result["status_code"]
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= expected_result["min_items"]


def test_get_metrics_includes_builtins(simulation_client):
    """Each builtin metric is present with expected description, scope, author."""
    client, _ = simulation_client
    response = client.get("/v1/simulations/metrics")

    expected_result = {"status_code": 200}
    assert response.status_code == expected_result["status_code"]
    data = response.json()
    by_key = {m["key"]: m for m in data}

    for key in BUILTIN_METRIC_KEYS:
        assert key in by_key, f"Missing metric: {key}"
        metric = by_key[key]
        expected_result = EXPECTED_METRICS[key]
        assert metric["display_name"] == expected_result["display_name"]
        assert metric["description"] == expected_result["description"]
        assert metric["scope"] == expected_result["scope"]
        assert metric["author"] == expected_result["author"]


def test_get_metrics_ordering_deterministic(simulation_client):
    """Result is sorted by key."""
    client, _ = simulation_client
    response = client.get("/v1/simulations/metrics")

    expected_result = {"status_code": 200}
    assert response.status_code == expected_result["status_code"]
    data = response.json()
    keys = [m["key"] for m in data]
    expected_result = sorted(keys)
    assert keys == expected_result


def test_get_metrics_schema_shape(simulation_client):
    """Each item has key, display_name, description, scope, author as strings; scope in turn|run."""
    client, _ = simulation_client
    response = client.get("/v1/simulations/metrics")

    expected_result = {"status_code": 200}
    assert response.status_code == expected_result["status_code"]
    data = response.json()
    expected_result = {
        "required_fields": {"key", "display_name", "description", "scope", "author"},
        "valid_scopes": {"turn", "run"},
    }

    for item in data:
        for field in expected_result["required_fields"]:
            assert field in item
        assert isinstance(item["key"], str)
        assert isinstance(item["display_name"], str)
        assert isinstance(item["description"], str)
        assert isinstance(item["scope"], str)
        assert isinstance(item["author"], str)
        assert item["scope"] in expected_result["valid_scopes"]
