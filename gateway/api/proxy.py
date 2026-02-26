"""HTTP proxy utilities for the FastAPI gateway."""

from __future__ import annotations

import logging
from typing import Iterable

import httpx
from fastapi import Request
from fastapi.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

_HOP_BY_HOP_HEADERS: frozenset[str] = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
        "host",
        "content-length",
    }
)


def _filter_headers(headers: Iterable[tuple[str, str]]) -> dict[str, str]:
    filtered: dict[str, str] = {}
    for k, v in headers:
        if k.lower() in _HOP_BY_HOP_HEADERS:
            continue
        filtered[k] = v
    return filtered


def _build_upstream_url(*, upstream_base_url: str, path: str, query: str) -> str:
    base = upstream_base_url.rstrip("/")
    url = f"{base}{path}"
    if query:
        url = f"{url}?{query}"
    return url


async def proxy_v1_request(
    *,
    request: Request,
    upstream_base_url: str,
    timeout_seconds: float,
    client: httpx.AsyncClient,
) -> Response:
    """Proxy a request to the configured upstream.

    MVP behavior:
    - Buffers request and response bodies in memory.
    - Forces identity encoding to avoid content-decoding mismatches.
    """
    upstream_url = _build_upstream_url(
        upstream_base_url=upstream_base_url,
        path=request.url.path,
        query=request.url.query,
    )

    upstream_headers = _filter_headers(request.headers.items())
    # Avoid automatic content decoding issues; we can remove this once we stream raw bytes.
    upstream_headers["accept-encoding"] = "identity"

    body = await request.body()

    try:
        upstream_response = await client.request(
            request.method,
            upstream_url,
            content=body,
            headers=upstream_headers,
            timeout=httpx.Timeout(timeout_seconds),
        )
    except httpx.TimeoutException:
        return JSONResponse(
            status_code=504,
            content={
                "error": {
                    "code": "UPSTREAM_TIMEOUT",
                    "message": "Upstream request timed out",
                    "detail": None,
                }
            },
        )
    except httpx.RequestError as exc:
        logger.warning("Upstream request failed: %s", exc)
        return JSONResponse(
            status_code=502,
            content={
                "error": {
                    "code": "UPSTREAM_UNAVAILABLE",
                    "message": "Upstream request failed",
                    "detail": None,
                }
            },
        )

    response_headers = _filter_headers(upstream_response.headers.items())
    return Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        headers=response_headers,
    )
