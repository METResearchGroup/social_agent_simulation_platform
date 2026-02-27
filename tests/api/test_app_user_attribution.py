"""Tests for Phase 2 app_user attribution: upsert on auth, run creation persists app_user_id."""

import sqlite3
import time

import jwt
from fastapi.testclient import TestClient

TEST_JWT_SECRET: str = "test-secret-for-app-user-attribution"
TEST_AUDIENCE: str = "authenticated"
AUTH_PROVIDER_ID: str = "test-app-user-sub-456"


def _make_valid_token(
    secret: str = TEST_JWT_SECRET,
    sub: str = AUTH_PROVIDER_ID,
    email: str | None = "appuser@example.com",
) -> str:
    """Create a valid Supabase-style JWT for testing."""
    payload = {
        "sub": sub,
        "aud": TEST_AUDIENCE,
        "exp": int(time.time()) + 3600,
        "role": "authenticated",
    }
    if email is not None:
        payload["email"] = email
    return jwt.encode(payload, secret, algorithm="HS256")


def _count_app_users(db_path: str) -> int:
    """Count rows in app_users table. Raises if table does not exist."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT count(*) as n FROM app_users").fetchone()
    conn.close()
    return row["n"]


def _count_app_users_with_auth_provider_id(db_path: str, auth_provider_id: str) -> int:
    """Count app_users rows with given auth_provider_id. Returns 0 if table does not exist."""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT count(*) as n FROM app_users WHERE auth_provider_id = ?",
            (auth_provider_id,),
        ).fetchone()
        conn.close()
        return row["n"]
    except sqlite3.OperationalError as e:
        if "no such table" in str(e):
            return 0
        raise


def _count_runs_with_app_user_id(db_path: str) -> int:
    """Count runs rows with non-null app_user_id. Returns 0 if column does not exist."""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT count(*) as n FROM runs WHERE app_user_id IS NOT NULL"
        ).fetchone()
        conn.close()
        return row["n"]
    except sqlite3.OperationalError as e:
        if "no such column" in str(e):
            return 0
        raise


def test_authenticated_request_upserts_app_user_row(
    client_with_temp_db, monkeypatch, tmp_path
):
    """Authenticated request upserts an app_user row keyed by JWT sub."""
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_JWT_SECRET)
    client: TestClient = client_with_temp_db
    db_path = str(tmp_path / "test.sqlite")
    token = _make_valid_token()

    assert _count_app_users_with_auth_provider_id(db_path, AUTH_PROVIDER_ID) == 0

    response = client.get(
        "/v1/simulations/config/default",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert _count_app_users_with_auth_provider_id(db_path, AUTH_PROVIDER_ID) == 1


def test_post_simulations_run_persists_app_user_id(
    client_with_temp_db, monkeypatch, tmp_path
):
    """POST /v1/simulations/run persists runs.app_user_id when authenticated."""
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_JWT_SECRET)
    client: TestClient = client_with_temp_db
    db_path = str(tmp_path / "test.sqlite")
    token = _make_valid_token()

    initial_runs_with_user = _count_runs_with_app_user_id(db_path)

    response = client.post(
        "/v1/simulations/run",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"num_agents": 1, "num_turns": 1},
    )

    assert response.status_code == 200
    assert _count_runs_with_app_user_id(db_path) == initial_runs_with_user + 1


def test_missing_email_claim_is_rejected(client_with_temp_db, monkeypatch, tmp_path):
    """Requests without an email claim now fail before touching the database."""
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_JWT_SECRET)
    client: TestClient = client_with_temp_db
    db_path = str(tmp_path / "test.sqlite")
    token = _make_valid_token(email=None)

    response = client.get(
        "/v1/simulations/config/default",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert _count_app_users_with_auth_provider_id(db_path, AUTH_PROVIDER_ID) == 0
