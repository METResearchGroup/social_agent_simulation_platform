"""Shared fixtures for API tests."""

from __future__ import annotations

from typing import cast

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request

from simulation.api.dependencies.app_user import require_current_app_user
from simulation.api.dependencies.auth import require_auth
from simulation.api.main import app


def _mock_require_current_app_user(
    request: Request, claims: dict = Depends(require_auth)
):
    """Bypass app_user DB upsert in tests; set request.state.current_app_user."""
    from lib.timestamp_utils import get_current_timestamp
    from simulation.core.models.app_user import AppUser

    ts = get_current_timestamp()
    email = claims.get("email", "test@example.com")
    display_name = (claims.get("user_metadata") or {}).get("full_name") or email

    app_user = AppUser(
        id="00000000-0000-0000-0000-000000000001",
        auth_provider_id=claims.get("sub", "test-user-id"),
        email=email,
        display_name=display_name,
        created_at=ts,
        last_seen_at=ts,
    )
    request.state.current_app_user = app_user
    return app_user


@pytest.fixture
def client_with_temp_db(tmp_path, monkeypatch):
    """TestClient using a temp SQLite DB for Phase 2 app_user attribution tests.

    Sets SIM_DB_PATH so migrations and requests use the temp DB. No auth override.
    """
    db_path = tmp_path / "test.sqlite"
    monkeypatch.setenv("SIM_DB_PATH", str(db_path))
    with TestClient(app=app) as client:
        yield client


def _mock_require_auth() -> dict:
    """Bypass JWT verification in tests. Returns minimal payload."""
    return {"sub": "test-user-id", "email": "test@example.com"}


@pytest.fixture
def simulation_client(temp_db):
    """TestClient for simulation API. Saves and restores app.state.engine after each test.

    Overrides require_auth to bypass JWT verification so simulation route tests
    do not need tokens.
    """
    original_engine = getattr(app.state, "engine", None)
    app.dependency_overrides[require_auth] = _mock_require_auth
    app.dependency_overrides[require_current_app_user] = _mock_require_current_app_user
    try:
        with TestClient(app=app) as client:
            fastapi_app = cast(FastAPI, client.app)
            yield client, fastapi_app
    finally:
        app.dependency_overrides.pop(require_auth, None)
        app.dependency_overrides.pop(require_current_app_user, None)
        app.state.engine = original_engine


@pytest.fixture
def client_no_auth_override():
    """TestClient without auth override. Used by test_auth to exercise real JWT verification."""
    with TestClient(app=app) as client:
        yield client
