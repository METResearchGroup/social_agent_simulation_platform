"""Structured request logging for API routes.

Provides a single log format (JSON-like key=value) for request start and
route completion so logs are parseable by aggregators and future metrics.
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def log_request_start(
    *,
    request_id: str,
    method: str,
    path: str,
    route: str | None = None,
) -> None:
    """Emit one structured log line at request start."""
    route = route or f"{method} {path}"
    payload = {
        "event": "request_start",
        "request_id": request_id,
        "route": route,
        "method": method,
        "path": path,
    }
    logger.info(_format_payload(payload))


def log_route_completion(
    *,
    request_id: str,
    route: str,
    latency_ms: int,
    run_id: str | None = None,
    status: str | None = None,
    error_code: str | None = None,
) -> None:
    """Emit one structured log line at route completion (success or error)."""
    payload: dict[str, Any] = {
        "event": "request_completed",
        "request_id": request_id,
        "route": route,
        "latency_ms": latency_ms,
    }
    if run_id is not None:
        payload["run_id"] = run_id
    if status is not None:
        payload["status"] = status
    if error_code is not None:
        payload["error_code"] = error_code
    logger.info(_format_payload(payload))


def _format_payload(payload: dict[str, Any]) -> str:
    """Serialize payload as a single line for log aggregators (JSON)."""
    return json.dumps(payload, sort_keys=True)
