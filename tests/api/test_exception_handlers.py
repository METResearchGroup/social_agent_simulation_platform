"""Tests for every exception handler registered in simulation/api/exception_handlers.py.

Mounts crash-test endpoints directly onto the real production app so that
SecurityHeadersMiddleware, RequestIdMiddleware, and EXCEPTION_HANDLERS are all
exercised exactly as they run in production.

The module-scoped fixture mounts the router temporarily and restores clean state
after the module finishes, so /test-errors/* routes do not leak into other tests.
"""

from unittest.mock import patch

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient

from simulation.api.dependencies.auth import UnauthorizedError
from simulation.api.errors import (
    ApiAgentFollowEdgeAlreadyExistsError,
    ApiAgentFollowEdgeNotFoundError,
    ApiAgentNotFoundError,
    ApiHandleAlreadyExistsError,
    ApiInvalidInputError,
    ApiRunCreationFailedError,
    ApiRunNotFoundError,
    ApiSelfFollowNotAllowedError,
    ApiTargetAgentNotFoundError,
    ApiValidationError,
)
from simulation.api.main import app

# ---------------------------------------------------------------------------
# Crash-test router: one endpoint per exception type
# ---------------------------------------------------------------------------

_router = APIRouter()


@_router.get("/trigger/run-not-found")
async def trigger_run_not_found():
    raise ApiRunNotFoundError(run_id="run-abc")


@_router.get("/trigger/run-creation-failed")
async def trigger_run_creation_failed():
    raise ApiRunCreationFailedError(message="engine returned no run")


@_router.get("/trigger/handle-already-exists")
async def trigger_handle_already_exists():
    raise ApiHandleAlreadyExistsError(handle="alice")


@_router.get("/trigger/agent-not-found")
async def trigger_agent_not_found():
    raise ApiAgentNotFoundError(handle="alice")


@_router.get("/trigger/target-agent-not-found")
async def trigger_target_agent_not_found():
    raise ApiTargetAgentNotFoundError(handle="bob")


@_router.get("/trigger/follow-edge-already-exists")
async def trigger_follow_edge_already_exists():
    raise ApiAgentFollowEdgeAlreadyExistsError(
        follower_handle="alice", target_handle="bob"
    )


@_router.get("/trigger/follow-edge-not-found")
async def trigger_follow_edge_not_found():
    raise ApiAgentFollowEdgeNotFoundError(follower_handle="alice", target_handle="bob")


@_router.get("/trigger/self-follow-not-allowed")
async def trigger_self_follow_not_allowed():
    raise ApiSelfFollowNotAllowedError(handle="alice")


@_router.get("/trigger/unauthorized")
async def trigger_unauthorized():
    raise UnauthorizedError(message="Token expired")


@_router.get("/trigger/value-error")
async def trigger_value_error():
    raise ValueError("generic value error")


@_router.get("/trigger/api-validation-error")
async def trigger_api_validation_error():
    raise ApiValidationError("specific validation failed")


@_router.get("/trigger/api-invalid-input")
async def trigger_api_invalid_input():
    raise ApiInvalidInputError("malformed ID format")


@_router.get("/trigger/internal-error")
async def trigger_internal_error():
    raise RuntimeError("unexpected crash")


# ---------------------------------------------------------------------------
# Fixture: mount router temporarily, restore clean state after module
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client():
    with (
        patch("simulation.api.main.initialize_database"),
        patch("simulation.api.main.build_app_context"),
    ):
        original_routes = list(app.router.routes)
        app.include_router(_router, prefix="/test-errors")
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c
        app.router.routes = original_routes
        app.openapi_schema = None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRunHandlers:
    def test_run_not_found_is_404(self, client):
        response = client.get("/test-errors/trigger/run-not-found")
        assert response.status_code == 404
        error = response.json()["error"]
        assert error["code"] == "RUN_NOT_FOUND"
        assert error["detail"] == "run-abc"
        # Verify both middlewares are in the response path for non-500 errors
        assert "x-content-type-options" in response.headers
        assert "x-request-id" in response.headers

    def test_run_creation_failed_is_500(self, client):
        response = client.get("/test-errors/trigger/run-creation-failed")
        assert response.status_code == 500
        error = response.json()["error"]
        assert error["code"] == "RUN_CREATION_FAILED"
        assert error["message"] == "engine returned no run"


class TestAgentHandlers:
    def test_handle_already_exists_is_409(self, client):
        response = client.get("/test-errors/trigger/handle-already-exists")
        assert response.status_code == 409
        error = response.json()["error"]
        assert error["code"] == "HANDLE_ALREADY_EXISTS"
        assert error["detail"] == "alice"

    def test_agent_not_found_is_404(self, client):
        response = client.get("/test-errors/trigger/agent-not-found")
        assert response.status_code == 404
        error = response.json()["error"]
        assert error["code"] == "AGENT_NOT_FOUND"
        assert error["detail"] == "alice"

    def test_target_agent_not_found_is_404(self, client):
        response = client.get("/test-errors/trigger/target-agent-not-found")
        assert response.status_code == 404
        error = response.json()["error"]
        assert error["code"] == "TARGET_AGENT_NOT_FOUND"
        assert error["detail"] == "bob"

    def test_follow_edge_already_exists_is_409(self, client):
        response = client.get("/test-errors/trigger/follow-edge-already-exists")
        assert response.status_code == 409
        error = response.json()["error"]
        assert error["code"] == "FOLLOW_EDGE_ALREADY_EXISTS"
        assert error["detail"] == "alice->bob"

    def test_follow_edge_not_found_is_404(self, client):
        response = client.get("/test-errors/trigger/follow-edge-not-found")
        assert response.status_code == 404
        error = response.json()["error"]
        assert error["code"] == "FOLLOW_EDGE_NOT_FOUND"
        assert error["detail"] == "alice->bob"

    def test_self_follow_not_allowed_is_422(self, client):
        response = client.get("/test-errors/trigger/self-follow-not-allowed")
        assert response.status_code == 422
        error = response.json()["error"]
        assert error["code"] == "SELF_FOLLOW_NOT_ALLOWED"
        assert error["detail"] == "alice"


class TestAuthHandler:
    def test_unauthorized_is_401(self, client):
        response = client.get("/test-errors/trigger/unauthorized")
        assert response.status_code == 401
        error = response.json()["error"]
        assert error["code"] == "UNAUTHORIZED"
        assert error["message"] == "Token expired"


class TestValueErrorHandlers:
    def test_generic_value_error_is_422(self, client):
        response = client.get("/test-errors/trigger/value-error")
        assert response.status_code == 422
        error = response.json()["error"]
        assert error["code"] == "VALIDATION_ERROR"
        assert "generic value error" in error["message"]

    def test_api_validation_error_is_422(self, client):
        response = client.get("/test-errors/trigger/api-validation-error")
        assert response.status_code == 422
        error = response.json()["error"]
        assert error["code"] == "VALIDATION_ERROR"
        assert "specific validation failed" in error["message"]

    def test_api_invalid_input_is_400_not_422(self, client):
        """ApiInvalidInputError must hit the isinstance branch and return 400, not 422."""
        response = client.get("/test-errors/trigger/api-invalid-input")
        assert response.status_code == 400
        error = response.json()["error"]
        assert error["code"] == "INVALID_INPUT"
        assert "malformed ID format" in error["message"]


class TestGlobalHandler:
    def test_unexpected_exception_is_500(self, client):
        response = client.get("/test-errors/trigger/internal-error")
        assert response.status_code == 500
        error = response.json()["error"]
        assert error["code"] == "INTERNAL_ERROR"
        assert error["message"] == "Internal server error."
