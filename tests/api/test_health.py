"""Smoke tests for the API health endpoint."""

from fastapi.testclient import TestClient

from simulation.api.main import app


def test_health_returns_200():
    """GET /health returns 200 and status ok."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
