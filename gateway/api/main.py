"""FastAPI gateway entrypoint.

Run locally (example):
  PYTHONPATH=. GATEWAY_UPSTREAM_BASE_URL=http://127.0.0.1:8000 \\
    uv run uvicorn gateway.api.main:app --reload --port 8001
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from gateway.api.proxy import proxy_v1_request
from gateway.api.settings import GatewaySettings
from lib.request_logging import log_request_start, log_route_completion
from lib.security_headers import SecurityHeadersMiddleware

logger = logging.getLogger(__name__)


class GatewayRequestLoggingMiddleware(BaseHTTPMiddleware):
    """Assigns request_id and emits request start/completion logs."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request.state.request_id = request_id

        route = f"{request.method} {request.url.path}"
        log_request_start(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            route=route,
        )

        start = time.perf_counter()
        response = await call_next(request)
        latency_ms = int((time.perf_counter() - start) * 1000)
        log_route_completion(
            request_id=request_id,
            route=route,
            latency_ms=latency_ms,
            status=str(getattr(response, "status_code", "")),
        )
        response.headers.setdefault("X-Request-ID", request_id)
        return response


def _allowed_origins_from_env() -> list[str]:
    # Note: parse ALLOWED_ORIGINS without requiring GATEWAY_UPSTREAM_BASE_URL at import time.
    raw = os.environ.get(
        "ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    )
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def create_app(*, settings: GatewaySettings | None = None) -> FastAPI:
    """Create a gateway app (exported for tests).

    If settings are not provided, they are loaded during startup. This keeps
    module import safe for tests while still failing fast on misconfiguration.
    """
    allowed_origins = (
        settings.allowed_origins if settings else _allowed_origins_from_env()
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Allow injection of a transport for tests by setting app.state.http_transport.
        transport = getattr(app.state, "http_transport", None)
        app.state.http_client = httpx.AsyncClient(transport=transport)
        app.state.settings = settings or GatewaySettings.from_env()
        try:
            yield
        finally:
            await app.state.http_client.aclose()

    app = FastAPI(title="Agent Simulation Platform Gateway", lifespan=lifespan)
    if settings is not None:
        # Avoid surprises in tests/tools that call the app without lifespan startup.
        app.state.settings = settings

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(GatewayRequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.api_route(
        "/v1/{full_path:path}",
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    )
    async def proxy_v1(request: Request, full_path: str):  # noqa: ARG001
        # CORSMiddleware handles preflight before reaching here.
        settings_obj: GatewaySettings = app.state.settings
        client: httpx.AsyncClient = app.state.http_client
        return await proxy_v1_request(
            request=request,
            upstream_base_url=settings_obj.upstream_base_url,
            timeout_seconds=settings_obj.timeout_seconds,
            client=client,
        )

    @app.exception_handler(RuntimeError)
    async def runtime_error_handler(
        request: Request, exc: RuntimeError
    ) -> JSONResponse:  # noqa: ARG001
        # Useful for missing env vars during dev.
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "GATEWAY_MISCONFIGURED",
                    "message": str(exc),
                    "detail": None,
                }
            },
        )

    return app


app = create_app()
