"""FastAPI application entrypoint.

Run from repository root with PYTHONPATH set to project root, e.g.:
    PYTHONPATH=. uv run uvicorn simulation.api.main:app --reload
"""

import asyncio
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY

from db.adapters.sqlite.sqlite import initialize_database
from lib.rate_limiting import limiter, rate_limit_exceeded_handler
from lib.request_logging import log_request_start
from lib.security_headers import SecurityHeadersMiddleware
from simulation.api.dependencies.auth import (
    UnauthorizedError,
    disallow_auth_bypass_in_production,
)
from simulation.api.routes.simulation import router as simulation_router
from simulation.core.factories import create_engine

DEFAULT_ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and simulation engine on startup."""
    await asyncio.to_thread(disallow_auth_bypass_in_production)
    await asyncio.to_thread(initialize_database)
    app.state.engine = await asyncio.to_thread(create_engine)
    yield


app = FastAPI(
    title="Agent Simulation Platform API",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)  # type: ignore[reportArgumentType]


def _unauthorized_handler(request: Request, exc: UnauthorizedError) -> JSONResponse:
    """Return 401 with standard error shape for auth failures."""
    return JSONResponse(
        status_code=401,
        content={
            "error": {
                "code": "UNAUTHORIZED",
                "message": exc.message,
                "detail": None,
            }
        },
    )


app.add_exception_handler(UnauthorizedError, _unauthorized_handler)  # type: ignore[reportArgumentType]


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Assigns request_id and logs request start in structured format."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request.state.request_id = request_id
        log_request_start(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )
        return await call_next(request)


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIdMiddleware)
_allowed_origins_raw: str = os.environ.get("ALLOWED_ORIGINS", DEFAULT_ALLOWED_ORIGINS)
_allowed_origins: list[str] = [
    origin.strip() for origin in _allowed_origins_raw.split(",") if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
app.include_router(simulation_router, prefix="/v1")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Return 422 with stable error shape matching other API errors."""
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


@app.get("/health")
def health():
    """Health check endpoint. Returns 200 when the service is up."""
    return {"status": "ok"}
