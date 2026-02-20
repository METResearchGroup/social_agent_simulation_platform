"""Structured request logging for API routes.

Provides a single log format (JSON-like key=value) for request start and
route completion so logs are parseable by aggregators and future metrics.
"""

import json
import logging
from collections.abc import Callable
from enum import Enum
from functools import wraps
from typing import Any, ParamSpec, cast

from starlette.requests import Request
from starlette.responses import Response


class RunIdSource(str, Enum):
    """Where to obtain run_id for completion logs."""

    RESPONSE = "response"
    PATH = "path"
    NONE = "none"


P = ParamSpec("P")

logger = logging.getLogger(__name__)


def _error_code_from_json_response(response: Response) -> str | None:
    """Extract error code from JSONResponse content if present."""
    content = getattr(response, "content", None)
    if isinstance(content, dict):
        return content.get("error", {}).get("code")
    if hasattr(response, "body") and response.body:
        try:
            raw = response.body
            if isinstance(raw, bytes):
                raw = raw.decode()
            else:
                raw = bytes(raw).decode()
            data = json.loads(raw)
            return data.get("error", {}).get("code")
        except (TypeError, ValueError):
            return None
    return None


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


def log_route_completion_decorator(
    *,
    route: str,
    success_type: type | tuple[type, ...],
    run_id_from: RunIdSource = RunIdSource.NONE,
) -> Callable[[Callable[P, Any]], Callable[P, Any]]:
    """Decorator that logs route completion after the handler returns.

    Wraps async route handlers. Extracts request_id and latency_ms from
    request.state, and run_id/status/error_code from the handler's return
    value. Use functools.wraps so FastAPI preserves the handler signature.
    """

    def decorator(func: Callable[P, Any]) -> Callable[P, Any]:
        @wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
            result = await func(*args, **kwargs)
            request = cast(Request | None, args[0] if args else kwargs.get("request"))
            if request is None:
                return result
            request_id: str = getattr(request.state, "request_id", "")
            latency_ms: int = getattr(request.state, "duration_ms", 0)
            success = isinstance(result, success_type)
            run_id: str | None
            if success:
                if run_id_from == RunIdSource.RESPONSE:
                    run_id = cast(str | None, getattr(result, "run_id", None))
                elif run_id_from == RunIdSource.PATH:
                    r = kwargs.get("run_id")
                    run_id = r if isinstance(r, str) else None
                else:
                    run_id = None
                status_obj = getattr(result, "status", None)
                status = getattr(status_obj, "value", None) if status_obj else "200"
                error_obj = getattr(result, "error", None)
                error_code = getattr(error_obj, "code", None) if error_obj else None
            else:
                if run_id_from in (RunIdSource.PATH, RunIdSource.RESPONSE):
                    r = kwargs.get("run_id")
                    run_id = r if isinstance(r, str) else None
                else:
                    run_id = None
                status = str(getattr(result, "status_code", "500"))
                error_code = _error_code_from_json_response(cast(Response, result))
            log_route_completion(
                request_id=request_id,
                route=route,
                latency_ms=latency_ms,
                run_id=run_id,
                status=status,
                error_code=error_code,
            )
            return result

        return async_wrapper

    return decorator


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
