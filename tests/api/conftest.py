"""Shared fixtures for API tests."""

from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from simulation.api.dependencies.auth import require_auth
from simulation.api.main import app


def _mock_require_auth() -> dict:
    """Bypass JWT verification in tests. Returns minimal payload."""
    return {"sub": "test-user-id", "email": "test@example.com"}


@pytest.fixture
def simulation_client():
    """TestClient for simulation API. Saves and restores app.state.engine after each test.

    Overrides require_auth to bypass JWT verification so simulation route tests
    do not need tokens.
    """
    original_engine = getattr(app.state, "engine", None)
    app.dependency_overrides[require_auth] = _mock_require_auth
    try:
        with TestClient(app=app) as client:
            fastapi_app = cast(FastAPI, client.app)
            yield client, fastapi_app
    finally:
        app.dependency_overrides.pop(require_auth, None)
        app.state.engine = original_engine


@pytest.fixture
def client_no_auth_override():
    """TestClient without auth override. Used by test_auth to exercise real JWT verification."""
    with TestClient(app=app) as client:
        yield client
