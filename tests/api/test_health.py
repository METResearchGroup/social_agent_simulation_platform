"""Smoke tests for the API health endpoint."""


class TestHealth:
    def test_health_returns_200(self, client):
        """GET /health returns 200 and status ok."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
