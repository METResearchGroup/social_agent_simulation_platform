"""Tests for security headers middleware."""

import pytest
from fastapi.testclient import TestClient

from simulation.api.main import app


@pytest.fixture
def client(temp_db):
    """Isolated DB so migrations do not depend on the repo's db.sqlite."""
    with TestClient(app) as client:
        yield client


class TestSecurityHeaders:
    def test_security_headers_present_on_health(self, client) -> None:
        """GET /health returns 200 and response includes security headers."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"

    def test_hsts_absent_when_disabled(
        self, client, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With ENABLE_HSTS unset or false, Strict-Transport-Security header is absent."""
        monkeypatch.delenv("ENABLE_HSTS", raising=False)
        response = client.get("/health")
        assert "Strict-Transport-Security" not in response.headers

    def test_hsts_present_when_enabled(
        self, client, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With ENABLE_HSTS=1, Strict-Transport-Security is present with max-age=31536000."""
        monkeypatch.setenv("ENABLE_HSTS", "1")
        response = client.get("/health")
        hsts = response.headers.get("Strict-Transport-Security")
        assert hsts is not None
        assert "max-age=31536000" in hsts
        assert "includeSubDomains" in hsts
