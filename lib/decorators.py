"""Shared decorators for timing and observability."""

import asyncio
import logging
import time
from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar

logger = logging.getLogger(__name__)

# Scale factor for converting seconds to milliseconds (used for elapsed_ms).
SECONDS_TO_MS: float = 1000.0

P = ParamSpec("P")
R = TypeVar("R")


def timed(
    *,
    log_level: int | None = logging.DEBUG,
    attach_attr: str | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator that records elapsed time for sync or async callables.

    Optionally logs at the given level (default DEBUG; pass None to disable)
    and/or attaches duration in ms to the first argument (e.g. request.state
    when first arg is a FastAPI Request).
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                start = time.perf_counter()
                try:
                    return await func(*args, **kwargs)
                finally:
                    _after_call(
                        func=func,
                        start=start,
                        log_level=log_level,
                        attach_attr=attach_attr,
                        first_arg=args[0] if args else None,
                    )

            return async_wrapper  # type: ignore[return-value]

        @wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                _after_call(
                    func=func,
                    start=start,
                    log_level=log_level,
                    attach_attr=attach_attr,
                    first_arg=args[0] if args else None,
                )

        return sync_wrapper  # type: ignore[return-value]

    return decorator


def _after_call(
    *,
    func: Callable[..., Any],
    start: float,
    log_level: int | None,
    attach_attr: str | None,
    first_arg: Any,
) -> None:
    elapsed_ms = int((time.perf_counter() - start) * SECONDS_TO_MS)
    if log_level is not None:
        logger.log(log_level, "%s completed in %dms", func.__qualname__, elapsed_ms)
    if attach_attr and first_arg is not None:
        target = getattr(first_arg, "state", first_arg)
        if hasattr(target, "__setattr__"):
            setattr(target, attach_attr, elapsed_ms)
