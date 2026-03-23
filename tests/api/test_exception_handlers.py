"""Tests for every exception handler registered in simulation/api/exception_handlers.py.

Uses a minimal crash-test FastAPI app with one endpoint per exception type,
so tests are isolated from business logic and run fast.
"""

from fastapi import APIRouter, FastAPI
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
from simulation.api.exception_handlers import EXCEPTION_HANDLERS

# ---------------------------------------------------------------------------
# Crash-test app: one endpoint per exception type
# ---------------------------------------------------------------------------

_app = FastAPI()
for _exc_class, _handler in EXCEPTION_HANDLERS.items():
    _app.add_exception_handler(_exc_class, _handler)  # type: ignore[arg-type]

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


_app.include_router(_router)

client = TestClient(_app, raise_server_exceptions=False)

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRunHandlers:
    def test_run_not_found_is_404(self):
        response = client.get("/trigger/run-not-found")
        assert response.status_code == 404
        error = response.json()["error"]
        assert error["code"] == "RUN_NOT_FOUND"
        assert error["detail"] == "run-abc"

    def test_run_creation_failed_is_500(self):
        response = client.get("/trigger/run-creation-failed")
        assert response.status_code == 500
        error = response.json()["error"]
        assert error["code"] == "RUN_CREATION_FAILED"
        assert error["message"] == "engine returned no run"


class TestAgentHandlers:
    def test_handle_already_exists_is_409(self):
        response = client.get("/trigger/handle-already-exists")
        assert response.status_code == 409
        error = response.json()["error"]
        assert error["code"] == "HANDLE_ALREADY_EXISTS"
        assert error["detail"] == "alice"

    def test_agent_not_found_is_404(self):
        response = client.get("/trigger/agent-not-found")
        assert response.status_code == 404
        error = response.json()["error"]
        assert error["code"] == "AGENT_NOT_FOUND"
        assert error["detail"] == "alice"

    def test_target_agent_not_found_is_404(self):
        response = client.get("/trigger/target-agent-not-found")
        assert response.status_code == 404
        error = response.json()["error"]
        assert error["code"] == "TARGET_AGENT_NOT_FOUND"
        assert error["detail"] == "bob"

    def test_follow_edge_already_exists_is_409(self):
        response = client.get("/trigger/follow-edge-already-exists")
        assert response.status_code == 409
        error = response.json()["error"]
        assert error["code"] == "FOLLOW_EDGE_ALREADY_EXISTS"
        assert error["detail"] == "alice->bob"

    def test_follow_edge_not_found_is_404(self):
        response = client.get("/trigger/follow-edge-not-found")
        assert response.status_code == 404
        error = response.json()["error"]
        assert error["code"] == "FOLLOW_EDGE_NOT_FOUND"
        assert error["detail"] == "alice->bob"

    def test_self_follow_not_allowed_is_422(self):
        response = client.get("/trigger/self-follow-not-allowed")
        assert response.status_code == 422
        error = response.json()["error"]
        assert error["code"] == "SELF_FOLLOW_NOT_ALLOWED"
        assert error["detail"] == "alice"


class TestAuthHandler:
    def test_unauthorized_is_401(self):
        response = client.get("/trigger/unauthorized")
        assert response.status_code == 401
        error = response.json()["error"]
        assert error["code"] == "UNAUTHORIZED"
        assert error["message"] == "Token expired"


class TestValueErrorHandlers:
    def test_generic_value_error_is_422(self):
        response = client.get("/trigger/value-error")
        assert response.status_code == 422
        error = response.json()["error"]
        assert error["code"] == "VALIDATION_ERROR"
        assert "generic value error" in error["message"]

    def test_api_validation_error_is_422(self):
        response = client.get("/trigger/api-validation-error")
        assert response.status_code == 422
        error = response.json()["error"]
        assert error["code"] == "VALIDATION_ERROR"
        assert "specific validation failed" in error["message"]

    def test_api_invalid_input_is_400_not_422(self):
        """ApiInvalidInputError must hit the isinstance branch and return 400, not 422."""
        response = client.get("/trigger/api-invalid-input")
        assert response.status_code == 400
        error = response.json()["error"]
        assert error["code"] == "INVALID_INPUT"
        assert "malformed ID format" in error["message"]


class TestGlobalHandler:
    def test_unexpected_exception_is_500(self):
        response = client.get("/trigger/internal-error")
        assert response.status_code == 500
        error = response.json()["error"]
        assert error["code"] == "INTERNAL_ERROR"
        assert error["message"] == "Internal server error."
