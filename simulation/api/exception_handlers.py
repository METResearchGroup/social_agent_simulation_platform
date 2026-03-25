import logging

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY

from lib.env_utils import is_local_mode
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
from simulation.api.routes._helpers import error_response

logger = logging.getLogger(__name__)


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "500 Internal Server Error: %s %s", request.method, request.url.path
    )
    return error_response(
        status_code=500,
        code="INTERNAL_ERROR",
        message="Internal server error.",
        detail=str(exc) if is_local_mode() else None,
    )


def validation_exception_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "detail": jsonable_encoder(exc.errors()),
            }
        },
    )


def unauthorized_handler(_request: Request, exc: UnauthorizedError) -> JSONResponse:
    return error_response(
        status_code=401,
        code="UNAUTHORIZED",
        message=exc.message,
    )


def run_not_found_handler(_request: Request, exc: ApiRunNotFoundError) -> JSONResponse:
    return error_response(
        status_code=404,
        code="RUN_NOT_FOUND",
        message="Run not found",
        detail=exc.run_id,
    )


def run_creation_failed_handler(
    _request: Request, exc: ApiRunCreationFailedError
) -> JSONResponse:
    return error_response(
        status_code=500,
        code="RUN_CREATION_FAILED",
        message=exc.message,
    )


def handle_already_exists_handler(
    _request: Request, exc: ApiHandleAlreadyExistsError
) -> JSONResponse:
    return error_response(
        status_code=409,
        code="HANDLE_ALREADY_EXISTS",
        message="Agent with this handle already exists",
        detail=exc.handle,
    )


def agent_not_found_handler(
    _request: Request, exc: ApiAgentNotFoundError
) -> JSONResponse:
    return error_response(
        status_code=404,
        code="AGENT_NOT_FOUND",
        message="Agent not found",
        detail=exc.handle,
    )


def target_agent_not_found_handler(
    _request: Request, exc: ApiTargetAgentNotFoundError
) -> JSONResponse:
    return error_response(
        status_code=404,
        code="TARGET_AGENT_NOT_FOUND",
        message="Target agent not found",
        detail=exc.handle,
    )


def follow_edge_already_exists_handler(
    _request: Request, exc: ApiAgentFollowEdgeAlreadyExistsError
) -> JSONResponse:
    return error_response(
        status_code=409,
        code="FOLLOW_EDGE_ALREADY_EXISTS",
        message="Follow edge already exists",
        detail=f"{exc.follower_handle}->{exc.target_handle}",
    )


def follow_edge_not_found_handler(
    _request: Request, exc: ApiAgentFollowEdgeNotFoundError
) -> JSONResponse:
    return error_response(
        status_code=404,
        code="FOLLOW_EDGE_NOT_FOUND",
        message="Follow edge not found",
        detail=f"{exc.follower_handle}->{exc.target_handle}",
    )


def self_follow_not_allowed_handler(
    _request: Request, exc: ApiSelfFollowNotAllowedError
) -> JSONResponse:
    return error_response(
        status_code=422,
        code="SELF_FOLLOW_NOT_ALLOWED",
        message="Agent cannot follow itself",
        detail=exc.handle,
    )


def value_error_handler(_request: Request, exc: ValueError) -> JSONResponse:
    if isinstance(exc, ApiInvalidInputError):
        return error_response(status_code=400, code="INVALID_INPUT", message=str(exc))
    if isinstance(exc, ApiValidationError):
        return error_response(
            status_code=422, code="VALIDATION_ERROR", message=str(exc)
        )
    return error_response(status_code=422, code="VALIDATION_ERROR", message=str(exc))


EXCEPTION_HANDLERS: dict[type[Exception], object] = {
    Exception: global_exception_handler,
    ValueError: value_error_handler,
    RequestValidationError: validation_exception_handler,
    UnauthorizedError: unauthorized_handler,
    ApiRunNotFoundError: run_not_found_handler,
    ApiRunCreationFailedError: run_creation_failed_handler,
    ApiHandleAlreadyExistsError: handle_already_exists_handler,
    ApiAgentNotFoundError: agent_not_found_handler,
    ApiTargetAgentNotFoundError: target_agent_not_found_handler,
    ApiAgentFollowEdgeAlreadyExistsError: follow_edge_already_exists_handler,
    ApiAgentFollowEdgeNotFoundError: follow_edge_not_found_handler,
    ApiSelfFollowNotAllowedError: self_follow_not_allowed_handler,
}
