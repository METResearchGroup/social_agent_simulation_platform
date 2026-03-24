"""FastAPI application entrypoint.

Run from repository root with PYTHONPATH set to project root, e.g.:
    PYTHONPATH=. uv run uvicorn simulation.api.main:app --reload
"""

import asyncio
import logging
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from db.adapters.sqlite.sqlite import get_db_path, initialize_database
from lib.env_utils import is_local_mode, parse_bool_env
from lib.rate_limiting import limiter, rate_limit_exceeded_handler
from lib.request_logging import log_request_start
from lib.security_headers import _hsts_enabled
from simulation.api.context import build_app_context
from simulation.api.dependencies.auth import disallow_auth_bypass_in_production
from simulation.api.exception_handlers import EXCEPTION_HANDLERS
from simulation.api.routes.simulation import router as simulation_router
from simulation.local_dev.local_mode import disallow_local_mode_in_production
from simulation.local_dev.seed_loader import seed_database_from_fixtures_if_needed

DEFAULT_ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

logger = logging.getLogger(__name__)


def _reset_local_db_if_requested() -> None:
    """When LOCAL_RESET_DB=1 in local mode, delete the local dummy DB file."""
    db_path = get_db_path()
    if os.path.exists(db_path):
        logger.warning("LOCAL_RESET_DB=1: deleting local dummy DB at %s", db_path)
        os.remove(db_path)
    else:
        logger.info(
            "LOCAL_RESET_DB=1: dummy DB did not exist (nothing to delete): %s",
            db_path,
        )


def _ensure_local_seed_data() -> None:
    """When in local mode, ensure seed data is loaded in the dummy DB."""
    db_path = get_db_path()
    logger.info("LOCAL=true: ensuring seed data in dummy DB at %s", db_path)
    seed_database_from_fixtures_if_needed(db_path=db_path)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and simulation engine on startup."""
    await asyncio.to_thread(disallow_auth_bypass_in_production)
    await asyncio.to_thread(disallow_local_mode_in_production)

    if is_local_mode() and parse_bool_env("LOCAL_RESET_DB"):
        await asyncio.to_thread(_reset_local_db_if_requested)

    await asyncio.to_thread(initialize_database)

    if is_local_mode():
        await asyncio.to_thread(_ensure_local_seed_data)
    else:
        logger.info(
            "Non-local API startup: fixture seed not applied in uvicorn lifespan "
            "(use LOCAL=true for the dummy dev DB, or Railway demo bootstrap before uvicorn)."
        )

    app.state.deps = await asyncio.to_thread(build_app_context)
    yield


class SecurityHeadersMiddleware:
    """Pure ASGI middleware that adds security headers to every HTTP response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["X-Content-Type-Options"] = "nosniff"
                headers["X-Frame-Options"] = "DENY"
                if _hsts_enabled():
                    headers["Strict-Transport-Security"] = (
                        "max-age=31536000; includeSubDomains"
                    )
            await send(message)

        await self.app(scope, receive, send_with_headers)


class RequestIdMiddleware:
    """Pure ASGI middleware that assigns a request ID and logs request start."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request.state.request_id = request_id
        log_request_start(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["X-Request-ID"] = request_id
            await send(message)

        await self.app(scope, receive, send_with_request_id)


app = FastAPI(
    title="Agent Simulation Platform API",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)  # type: ignore[reportArgumentType]

for exc_class, handler_func in EXCEPTION_HANDLERS.items():
    app.add_exception_handler(exc_class, handler_func)  # type: ignore[reportArgumentType]

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
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIdMiddleware)
app.include_router(simulation_router, prefix="/v1")


@app.get("/health")
def health():
    """Health check endpoint. Returns 200 when the service is up."""
    return {"status": "ok"}
