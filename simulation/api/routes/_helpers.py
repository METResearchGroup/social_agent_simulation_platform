"""Shared route helpers for simulation API."""

from fastapi.responses import JSONResponse


def error_response(
    status_code: int,
    code: str,
    message: str,
    detail: str | None = None,
) -> JSONResponse:
    """Return a JSONResponse with the standard error payload shape."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "detail": detail,
            }
        },
    )
