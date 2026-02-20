"""Tests for JWT authentication on protected routes."""

import time

import jwt
from fastapi.testclient import TestClient

TEST_JWT_SECRET: str = "test-secret-for-auth-tests-only"
TEST_AUDIENCE: str = "authenticated"


def _make_valid_token(secret: str = TEST_JWT_SECRET) -> str:
    """Create a valid Supabase-style JWT for testing."""
    payload = {
        "sub": "test-user-123",
        "email": "test@example.com",
        "aud": TEST_AUDIENCE,
        "exp": int(time.time()) + 3600,
        "role": "authenticated",
    }
    return jwt.encode(
        payload,
        secret,
        algorithm="HS256",
    )


def test_protected_route_without_token_returns_401(client_no_auth_override):
    """Request to /v1/simulations/config/default without Authorization returns 401."""
    client: TestClient = client_no_auth_override
    response = client.get("/v1/simulations/config/default")

    assert response.status_code == 401
    data = response.json()
    expected = {
        "error": {
            "code": "UNAUTHORIZED",
            "message": "Missing or invalid Authorization header",
            "detail": None,
        }
    }
    assert data == expected


def test_protected_route_with_invalid_token_returns_401(
    client_no_auth_override, monkeypatch
):
    """Request with malformed or invalid token returns 401."""
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_JWT_SECRET)
    client: TestClient = client_no_auth_override
    headers = {"Authorization": "Bearer invalid-token"}

    response = client.get("/v1/simulations/config/default", headers=headers)

    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "UNAUTHORIZED"
    assert "Invalid or expired" in data["error"]["message"]


def test_protected_route_with_valid_token_returns_200(
    client_no_auth_override, monkeypatch
):
    """Request with valid Supabase JWT returns 200."""
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_JWT_SECRET)
    token = _make_valid_token()
    client: TestClient = client_no_auth_override
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/v1/simulations/config/default", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert "num_agents" in data
    assert "num_turns" in data


def test_health_route_remains_public(client_no_auth_override):
    """GET /health does not require authentication."""
    client: TestClient = client_no_auth_override
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
