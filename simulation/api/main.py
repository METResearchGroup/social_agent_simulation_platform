"""FastAPI application entrypoint.

Run from repository root with PYTHONPATH set to project root, e.g.:
    PYTHONPATH=. uv run uvicorn simulation.api.main:app --reload
"""

import asyncio
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY

from db.adapters.sqlite.sqlite import initialize_database
from lib.request_logging import log_request_start
from simulation.api.routes.simulation import router as simulation_router
from simulation.core.factories import create_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and simulation engine on startup."""
    await asyncio.to_thread(initialize_database)
    app.state.engine = await asyncio.to_thread(create_engine)
    yield


app = FastAPI(
    title="Agent Simulation Platform API",
    lifespan=lifespan,
)


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


app.add_middleware(RequestIdMiddleware)
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
