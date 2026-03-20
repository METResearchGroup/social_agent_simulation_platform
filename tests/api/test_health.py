"""Smoke tests for the API health endpoint."""

import pytest
from fastapi.testclient import TestClient

from simulation.api.main import app


@pytest.fixture
def client(temp_db):
    """Isolated DB so migrations do not depend on the repo's db.sqlite."""
    with TestClient(app) as client:
        yield client


class TestHealth:
    def test_health_returns_200(self, client):
        """GET /health returns 200 and status ok."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
